# coding=utf-8

import unittest
from mock import patch
import activity.activity_FindPreprintPDF as activity_module
from activity.activity_FindPreprintPDF import (
    activity_FindPreprintPDF as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestFindPreprintPdf(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch("requests.get")
    def test_do_activity(
        self,
        fake_get,
        fake_session,
    ):
        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        fake_get.return_value = FakeResponse(
            200,
            response_json={"pdf": pdf_url},
        )
        fake_session.return_value = FakeSession(SESSION_DICT)
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertTrue(
            "FindPreprintPDF, get url https://api/path/95901v1"
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            "FindPreprintPDF, for article_id %s version %s got pdf_url %s"
            % (SESSION_DICT.get("article_id"), SESSION_DICT.get("version"), pdf_url)
            in self.activity.logger.loginfo,
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "get_preprint_pdf_url")
    def test_do_activity_endpoint_exception(
        self,
        fake_get_preprint_pdf_url,
        fake_session,
    ):
        "test if an exception is raised when getting pdf_url from the endpoint"
        exception_message = "An exception"
        fake_get_preprint_pdf_url.side_effect = RuntimeError(exception_message)

        fake_session.return_value = FakeSession(SESSION_DICT)
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "FindPreprintPDF, exception raised getting pdf_url"
                " from endpoint https://api/path/95901v1: %s"
            )
            % exception_message,
        )


class TestSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.reviewed_preprint_api_endpoint = (
            settings_mock.reviewed_preprint_api_endpoint
        )

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.reviewed_preprint_api_endpoint = (
            self.reviewed_preprint_api_endpoint
        )

    @patch.object(activity_module, "get_session")
    def test_missing_settings(self, fake_session):
        "test if settings is missing a required value"
        fake_session.return_value = FakeSession(SESSION_DICT)
        del settings_mock.reviewed_preprint_api_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "FindPreprintPDF, reviewed_preprint_api_endpoint in settings is missing, skipping",
        )

    @patch.object(activity_module, "get_session")
    def test_blank_settings(self, fake_session):
        "test if required settings value is blank"
        fake_session.return_value = FakeSession(SESSION_DICT)
        settings_mock.reviewed_preprint_api_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "FindPreprintPDF, reviewed_preprint_api_endpoint in settings is blank, skipping",
        )


class TestGetPreprintPdfUrl(unittest.TestCase):
    "tests for get_preprint_pdf_url()"

    def setUp(self):
        article_id = 95901
        version = 1
        self.endpoint_url = settings_mock.reviewed_preprint_api_endpoint.format(
            article_id=article_id, version=version
        )
        self.caller_name = "FindPreprintPDF"
        self.user_agent = "user-agent"

    @patch("requests.get")
    def test_200(self, fake_get):
        "test status code 200"
        pdf_url = "https://example.org/article.pdf"
        fake_get.return_value = FakeResponse(
            200,
            response_json={"pdf": pdf_url},
        )
        # invoke
        result = activity_module.get_preprint_pdf_url(
            self.endpoint_url, self.caller_name, self.user_agent
        )
        # assert
        self.assertEqual(result, pdf_url)

    @patch("requests.get")
    def test_404(self, fake_get):
        "test status code 404"
        fake_get.return_value = FakeResponse(
            404,
            response_json={"title": "not found"},
        )
        # invoke
        result = activity_module.get_preprint_pdf_url(
            self.endpoint_url, self.caller_name, self.user_agent
        )
        # assert
        self.assertEqual(result, None)

    @patch("requests.get")
    def test_500(self, fake_get):
        "test status code 500"
        fake_get.return_value = FakeResponse(500)
        # invoke and assert
        with self.assertRaises(RuntimeError):
            activity_module.get_preprint_pdf_url(
                self.endpoint_url, self.caller_name, self.user_agent
            )
