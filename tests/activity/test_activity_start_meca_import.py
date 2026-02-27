# coding=utf-8

import unittest
from mock import patch
from provider import requests_provider
import activity.activity_StartMecaImport as activity_module
from activity.activity_StartMecaImport import (
    activity_StartMecaImport as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestStartMecaImport(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(requests_provider, "post_to_endpoint")
    def test_do_activity(
        self,
        fake_post,
        fake_session,
    ):
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        fake_post.return_value = FakeResponse(200, content="Import started ...")
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(requests_provider, "post_to_endpoint")
    def test_post_exception(
        self,
        fake_post,
        fake_session,
    ):
        "test if POST raises an exception"
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        fake_post.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.meca_import_endpoint = settings_mock.meca_import_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_import_endpoint = self.meca_import_endpoint

    @patch.object(activity_module, "get_session")
    def test_missing_settings(self, fake_session):
        "test if settings is missing a required value"
        fake_session.return_value = FakeSession(SESSION_DICT)
        del settings_mock.meca_import_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "StartMecaImport, meca_import_endpoint in settings is missing, skipping",
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.meca_import_endpoint = settings_mock.meca_import_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_import_endpoint = self.meca_import_endpoint

    @patch.object(activity_module, "get_session")
    def test_blank_settings(self, fake_session):
        "test if required settings value is blank"
        fake_session.return_value = FakeSession(SESSION_DICT)
        settings_mock.meca_import_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "StartMecaImport, meca_import_endpoint in settings is blank, skipping",
        )
