# coding=utf-8

import unittest
import copy
import os
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider, meca
import activity.activity_ValidateJatsDtd as activity_module
from activity.activity_ValidateJatsDtd import (
    activity_ValidateJatsDtd as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeStorageContext,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestValidateJatsDtd(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
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
        xml_string = b"<root/>"
        validation_content = b'{\n  "status":"valid"\n}'
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(self.activity.statuses.get("valid"), True)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_post_xml_file_content_empty(
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
        xml_string = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = None
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(activity_module, "storage_context")
    def test_post_xml_file_exception(
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
        xml_string = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issue")
    @patch.object(activity_module, "storage_context")
    def test_invalid_response(
        self,
        fake_storage_context,
        fake_find_github_issue,
        fake_post_xml_file,
        fake_session,
    ):
        "test response content for invalid XML"
        fake_find_github_issue.return_value = FakeGithubIssue()
        directory = TempDirectory()
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        errors = b"[]"
        validation_content = b'{\n  "status":"invalid",\n  "errors":%s\n}' % errors
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            mock_session.get_value("log_messages"),
            (
                "\n%s, validation error for version DOI %s file %s/content/24301711.xml: %s"
            )
            % (
                self.activity.name,
                SESSION_DICT.get("version_doi"),
                self.activity.directories.get("INPUT_DIR"),
                errors.decode("utf-8"),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issue")
    @patch.object(activity_module, "storage_context")
    def test_github_exception(
        self,
        fake_storage_context,
        fake_find_github_issue,
        fake_post_xml_file,
        fake_session,
    ):
        "test if Github communication raises an error"
        fake_find_github_issue.side_effect = Exception("An exception")
        directory = TempDirectory()
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        errors = b"[]"
        validation_content = b'{\n  "status":"invalid",\n  "errors":%s\n}' % errors
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception when adding a comment to Github for version DOI %s "
                "file %s/content/24301711.xml. Details: An exception"
            )
            % (
                self.activity.name,
                SESSION_DICT.get("version_doi"),
                self.activity.directories.get("INPUT_DIR"),
            ),
        )
        self.assertEqual(
            mock_session.get_value("log_messages"),
            (
                "\n%s, validation error for version DOI %s file %s/content/24301711.xml: %s"
            )
            % (
                self.activity.name,
                SESSION_DICT.get("version_doi"),
                self.activity.directories.get("INPUT_DIR"),
                errors.decode("utf-8"),
            ),
        )


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.meca_dtd_endpoint = settings_mock.meca_dtd_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_dtd_endpoint = self.meca_dtd_endpoint

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.meca_dtd_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "ValidateJatsDtd, meca_dtd_endpoint in settings is missing, skipping",
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.meca_dtd_endpoint = settings_mock.meca_dtd_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_dtd_endpoint = self.meca_dtd_endpoint

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.meca_dtd_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "ValidateJatsDtd, meca_dtd_endpoint in settings is blank, skipping",
        )
