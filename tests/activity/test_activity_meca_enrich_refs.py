# coding=utf-8

import unittest
import copy
import os
from mock import patch
from testfixtures import TempDirectory
from provider import meca
import activity.activity_MecaEnrichRefs as activity_module
from activity.activity_MecaEnrichRefs import (
    activity_MecaEnrichRefs as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeStorageContext,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestMecaEnrichRefs(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        activity_module.SLEEP_SECONDS = 0.001
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self,
        fake_storage_context,
        fake_post_xml_file,
        fake_session,
    ):
        directory = TempDirectory()
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        start_xml = b"<root/>"
        transformed_xml = b"<root>Modified.</root>"
        with open(destination_path, "wb") as open_file:
            open_file.write(start_xml)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = transformed_xml
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        with open(destination_path, "rb") as open_file:
            self.assertEqual(open_file.read(), transformed_xml)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_post_content_empty(
        self,
        fake_storage_context,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST response content returned is empty"
        directory = TempDirectory()
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        start_xml = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(start_xml)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = None
        expected_result = activity_class.ACTIVITY_TEMPORARY_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_post_to_xsl_exception(
        self,
        fake_storage_context,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST raises an exception"
        directory = TempDirectory()
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        start_xml = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(start_xml)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_TEMPORARY_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_post_exception_max_attempts(
        self,
        fake_storage_context,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST raises an exception and is the final attempt"
        directory = TempDirectory()
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        # set the session counter value
        mock_session.store_value(activity_module.SESSION_ATTEMPT_COUNTER_NAME, 1000000)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        start_xml = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(start_xml)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    def test_silent_correction(self, fake_session):
        "test a silent-correction"
        silent_session_dict = copy.copy(SESSION_DICT)
        silent_session_dict["run_type"] = "silent-correction"
        fake_session.return_value = FakeSession(silent_session_dict)
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "MecaEnrichRefs, will not be invoked as part of a silent-correction, skipping",
        )


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.meca_enrich_refs_endpoint = settings_mock.meca_enrich_refs_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_enrich_refs_endpoint = self.meca_enrich_refs_endpoint

    @patch.object(activity_module, "get_session")
    def test_missing_settings(self, fake_session):
        "test if settings is missing a required value"
        fake_session.return_value = FakeSession(SESSION_DICT)
        del settings_mock.meca_enrich_refs_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "MecaEnrichRefs, meca_enrich_refs_endpoint in settings is missing, skipping",
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.meca_enrich_refs_endpoint = settings_mock.meca_enrich_refs_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_enrich_refs_endpoint = self.meca_enrich_refs_endpoint

    @patch.object(activity_module, "get_session")
    def test_blank_settings(self, fake_session):
        "test if required settings value is blank"
        fake_session.return_value = FakeSession(SESSION_DICT)
        settings_mock.meca_enrich_refs_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "MecaEnrichRefs, meca_enrich_refs_endpoint in settings is blank, skipping",
        )
