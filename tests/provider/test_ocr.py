import unittest
from mock import patch
from provider import ocr
from tests import settings_mock
from tests.activity import test_activity_data
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


class TestOcrFiles(unittest.TestCase):
    "test ocr_files()"

    def setUp(self):
        self.caller_name = "AcceptedSubmissionPeerReviewOcr"
        self.logger = FakeLogger()
        self.file_name = "sa1-inf1.jpg"
        self.file_path = "tests/files_source/digests/outbox/99999/digest-99999.jpg"
        self.file_to_path_map = {self.file_name: self.file_path}
        self.identifier = "test.zip"

    @patch("provider.ocr.requests.post")
    def test_ocr_files(self, fake_request):
        "test a request to the ocr endpoint but mocking the requests.post"
        options_type = "math"
        app_type = "default"
        response_json = {}
        response_status = 200
        response = FakeResponse(response_status)
        response.response_json = response_json
        fake_request.return_value = response
        expected_result = {self.file_name: response_json}
        # invoke
        result = ocr.ocr_files(
            self.file_to_path_map,
            options_type,
            app_type,
            settings_mock,
            self.caller_name,
            self.logger,
            self.identifier,
        )
        # assert
        self.assertDictEqual(result, expected_result)

    @patch("requests.post")
    def test_table_ocr_files(self, fake_request):
        "test the options_type table"
        options_type = "table"
        app_type = "preprint"
        response_json = {"data": [{"type": "tsv", "value": ""}]}
        response_status = 200
        response = FakeResponse(response_status, response_json)
        # response.response_json = response_json
        fake_request.return_value = response
        expected_result = {self.file_name: response_json}
        # invoke
        result = ocr.ocr_files(
            self.file_to_path_map,
            options_type,
            app_type,
            settings_mock,
            self.caller_name,
            self.logger,
            self.identifier,
        )
        # assert
        self.assertDictEqual(result, expected_result)

    @patch("requests.post")
    def test_failure_status_code(self, fake_request):
        "test exception catching of a non-success status code response"
        options_type = "math"
        app_type = None
        response_json = {}
        response_status = 500
        response = FakeResponse(response_status)
        response.response_json = response_json
        fake_request.return_value = response
        expected_result = {}
        excepted_log_message = (
            "%s, exception posting to Mathpix API endpoint, file_name %s: "
            "Error in mathpix_post_request %s to Mathpix API: %s\nNone"
            % (self.caller_name, self.file_name, self.file_path, response_status)
        )
        # invoke
        result = ocr.ocr_files(
            self.file_to_path_map,
            options_type,
            app_type,
            settings_mock,
            self.caller_name,
            self.logger,
            self.identifier,
        )
        # assert
        self.assertDictEqual(result, expected_result)
        # test for logging
        self.assertEqual(self.logger.logexception, excepted_log_message)


EQUATION_DATA = test_activity_data.EXAMPLE_OCR_RESPONSE_JSON.get("data")


class TestMathDataParts(unittest.TestCase):
    "test math_data_parts()"

    def test_math_data_parts(self):
        "test expected input"
        math_data = EQUATION_DATA
        mathml_data, latex_data = ocr.math_data_parts(math_data)
        self.assertTrue(isinstance(mathml_data, dict))
        self.assertTrue(isinstance(latex_data, dict))
        self.assertEqual(list(mathml_data.keys()), ["type", "value"])
        self.assertEqual(list(latex_data.keys()), ["type", "value"])

    def test_empty_list(self):
        "test when data is an empty list"
        math_data = []
        mathml_data, latex_data = ocr.math_data_parts(math_data)
        self.assertEqual(mathml_data, None)
        self.assertEqual(latex_data, None)
