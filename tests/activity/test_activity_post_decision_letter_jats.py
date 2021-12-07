# coding=utf-8

import os
import unittest
from mock import patch
import activity.activity_PostDecisionLetterJATS as activity_module
from activity.activity_PostDecisionLetterJATS import (
    activity_PostDecisionLetterJATS as activity_object,
)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeSession, FakeStorageContext
from tests.classes_mock import FakeSMTPServer


SESSION_DATA = {
    "bucket_folder_name": "elife39122",
    "xml_file_name": "elife-39122.xml",
}


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_decision_letter_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


class TestPostDecisionLetterJats(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.activity = activity_object(
            settings_mock, self.fake_logger, None, None, None
        )
        self.input_data = input_data("elife-39122.zip")

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.post")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity(
        self,
        fake_download_storage_context,
        requests_method_mock,
        fake_email_smtp_connect,
        mock_session,
    ):
        expected_result = activity_object.ACTIVITY_SUCCESS
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # mock the session
        fake_session = FakeSession(SESSION_DATA)
        mock_session.return_value = fake_session
        # POST response
        requests_method_mock.return_value = FakeResponse(200, None)
        # do the activity
        result = self.activity.do_activity(self.input_data)
        # check assertions
        self.assertEqual(result, expected_result)
        xml_file_name = self.activity.xml_file.split(os.sep)[-1]
        self.assertEqual(xml_file_name, "elife-39122.xml")
        self.assertEqual(self.activity.doi, "10.7554/eLife.39122")

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.post")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_post_failed(
        self,
        fake_download_storage_context,
        requests_method_mock,
        fake_email_smtp_connect,
        mock_session,
    ):
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # mock the session
        fake_session = FakeSession(SESSION_DATA)
        mock_session.return_value = fake_session
        # POST response
        requests_method_mock.return_value = FakeResponse(500, None)
        # do the activity
        result = self.activity.do_activity(self.input_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertTrue(
            self.activity.post_error_message.startswith(
                "POST was not successful, details: Error posting decision letter JATS to endpoint"
                " https://typesetter/updatedigest: status_code: 500\n"
                "request headers: {}\n"
                "request body: None\n"
                "response headers: {}\n"
                "response: None"
            )
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(activity_module.requests_provider, "post_to_endpoint")
    def test_do_activity_post_exception(
        self,
        fake_post_jats,
        fake_download_storage_context,
        fake_email_smtp_connect,
        mock_session,
    ):
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # mock the session
        fake_session = FakeSession(SESSION_DATA)
        mock_session.return_value = fake_session
        # exception in post
        fake_post_jats.side_effect = Exception("Something went wrong!")
        # do the activity
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, expected_result)
        self.assertTrue(self.activity.statuses.get("error_email"))
        self.assertEqual(
            self.fake_logger.logexception,
            "Exception raised in do_activity. Details: Something went wrong!",
        )

    @patch.object(activity_module, "get_session")
    def test_do_activity_bad_session(self, mock_session):
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        # mock the session
        fake_session = FakeSession({})
        mock_session.return_value = fake_session

        # do the activity
        result = self.activity.do_activity(self.input_data)

        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.fake_logger.logerror, "Missing session data in PostDecisionLetterJATS."
        )


class TestPostDecisionLetterBadSettings(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.activity = activity_object(
            settings_mock, self.fake_logger, None, None, None
        )
        self.input_data = input_data("elife-39122.zip")

    @patch.object(activity_module, "get_session")
    def test_do_activity_missing_endpoint(self, mock_session):
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        # mock the session
        fake_session = FakeSession(SESSION_DATA)
        mock_session.return_value = fake_session

        # remove the setting value
        del self.activity.settings.typesetter_decision_letter_endpoint

        # do the activity
        result = self.activity.do_activity(self.input_data)

        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.fake_logger.logerror,
            "No typesetter endpoint in settings, skipping PostDecisionLetterJATS.",
        )

    @patch.object(activity_module, "get_session")
    def test_do_activity_blank_endpoint(self, mock_session):
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE

        # mock the session
        fake_session = FakeSession(SESSION_DATA)
        mock_session.return_value = fake_session

        # remove the setting value
        self.activity.settings.typesetter_decision_letter_endpoint = None

        # do the activity
        result = self.activity.do_activity(self.input_data)

        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.fake_logger.logerror,
            "Typesetter endpoint in settings is blank, skipping PostDecisionLetterJATS.",
        )
