import unittest
from mock import patch
from provider import ocr
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


class TestMathpixTablePostRequest(unittest.TestCase):
    "tests for provider.ocr.mathpix_table_post_request()"

    def setUp(self):
        self.url = settings_mock.mathpix_endpoint
        self.app_id = settings_mock.mathpix_app_id
        self.app_key = settings_mock.mathpix_app_key
        self.logger = FakeLogger()
        self.file_path = "tests/files_source/digests/outbox/99999/digest-99999.jpg"
        self.options_json = None
        self.response_content_success = None
        self.response_json_success = {"data": [{"type": "tsv", "value": ""}]}

    @patch("requests.post")
    def test_mathpix_table_post_request_201(self, mock_requests_post):
        verify_ssl = False
        response_status_code = 201
        response = FakeResponse(response_status_code)
        response.content = self.response_content_success
        response.response_json = self.response_json_success
        mock_requests_post.return_value = response

        ocr.mathpix_table_post_request(
            self.url,
            self.app_id,
            self.app_key,
            self.file_path,
            self.options_json,
            verify_ssl,
            self.logger,
        )

        self.assertEqual(
            self.logger.loginfo[-1],
            "Response from Mathpix API: %s\n%s"
            % (response_status_code, self.response_content_success),
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "Post file %s to Mathpix API: POST %s\n" % (self.file_path, self.url),
        )


class TestMathpixPostRequest(unittest.TestCase):
    def setUp(self):
        self.url = settings_mock.mathpix_endpoint
        self.app_id = settings_mock.mathpix_app_id
        self.app_key = settings_mock.mathpix_app_key
        self.logger = FakeLogger()
        self.file_path = "tests/files_source/digests/outbox/99999/digest-99999.jpg"
        self.options_json = None
        self.response_content_success = None
        self.response_json_success = {"data": [{"type": "latex", "value": ""}]}

    @patch("requests.post")
    def test_mathpix_post_request_201(self, mock_requests_post):
        verify_ssl = False
        response_status_code = 201
        response = FakeResponse(response_status_code)
        response.content = self.response_content_success
        response.response_json = self.response_json_success
        mock_requests_post.return_value = response

        ocr.mathpix_post_request(
            self.url,
            self.app_id,
            self.app_key,
            self.file_path,
            self.options_json,
            verify_ssl,
            self.logger,
        )

        self.assertEqual(
            self.logger.loginfo[-1],
            "Response from Mathpix API: %s\n%s"
            % (response_status_code, self.response_content_success),
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "Post file %s to Mathpix API: POST %s\n" % (self.file_path, self.url),
        )

    @patch("requests.post")
    def test_mathpix_post_request_400(self, mock_requests_post):
        verify_ssl = False
        response = FakeResponse(400)
        mock_requests_post.return_value = response
        self.assertRaises(
            Exception,
            ocr.mathpix_post_request,
            self.url,
            self.app_id,
            self.app_key,
            self.file_path,
            self.options_json,
            verify_ssl,
            self.logger,
        )
