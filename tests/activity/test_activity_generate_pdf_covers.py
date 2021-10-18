import unittest
import json
from mock import patch
from provider.article import article
from provider import lax_provider
from activity.activity_GeneratePDFCovers import activity_GeneratePDFCovers
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


class TestGeneratePDFCovers(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.generatepdfcovers = activity_GeneratePDFCovers(
            settings_mock, self.fake_logger, None, None, None)
        self.data = {
            "run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
            "article_id": "353",
            "version": "1"}
        self.article_snippet = {
            'subjects': [
                {
                    "id": "neuroscience",
                    "name": "Neuroscience"
                }]
            }

    def test_do_activity_bad_data(self):
        data = None
        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(self.fake_logger.logerror[:36], "Error retrieving basic article data.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)
        json.dumps(self.fake_logger.logerror)

    @patch.object(lax_provider, 'article_snippet')
    @patch('requests.post')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_404(self, fake_monitor_event, fake_request, fake_snippet):
        fake_request.return_value = FakeResponse(404, {})
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(self.fake_logger.logerror[:20], "PDF cover not found.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)
        json.dumps(self.fake_logger.logerror)

    @patch.object(lax_provider, 'article_snippet')
    @patch('requests.post')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_500(self, fake_monitor_event, fake_request, fake_snippet):
        fake_request.return_value = FakeResponse(500, {})
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(
            self.fake_logger.logerror[:44], "unhandled status code from PDF cover service")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)
        json.dumps(self.fake_logger.logerror)

    @patch.object(lax_provider, 'article_snippet')
    @patch.object(article, 'get_pdf_cover_link')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_wrong_result_from_covers(
            self, fake_monitor_event, fake_article_pdf_cover_link, fake_snippet):
        fake_article_pdf_cover_link.return_value = ""
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(self.fake_logger.logerror[:44], "Unexpected result from pdf covers API.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)
        json.dumps(self.fake_logger.logerror)

    @patch.object(lax_provider, 'article_snippet')
    @patch.object(article, 'get_pdf_cover_link')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_get_pdf_exception(
            self, fake_monitor_event, fake_article_pdf_cover_link, fake_snippet):
        exception_message = 'Exception for unknown reason'
        fake_article_pdf_cover_link.side_effect = Exception(exception_message)
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(self.fake_logger.logerror[:44], exception_message)
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)
        json.dumps(self.fake_logger.logerror)

    @patch.object(lax_provider, 'article_snippet')
    @patch('requests.post')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_success_first_generation(
            self, fake_monitor_event, fake_request, fake_snippet):
        fake_request.return_value = FakeResponse(
            202,
            {
                "formats": {
                    "a4": "https://s3.eu-west-2.amazonaws.com/a4/09560",
                    "letter": "https://s3.eu-west-2.amazonaws.com/letter/09560"
                }
            })
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_SUCCESS)

    @patch.object(lax_provider, 'article_snippet')
    @patch('requests.post')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_success_already_existing(
            self, fake_monitor_event, fake_request, fake_snippet):
        fake_request.return_value = FakeResponse(
            200,
            {
                "formats": {
                    "a4": "https://s3.eu-west-2.amazonaws.com/a4/09560",
                    "letter": "https://s3.eu-west-2.amazonaws.com/letter/09560"
                }
            })
        fake_snippet.return_value = self.article_snippet

        result = self.generatepdfcovers.do_activity(self.data)

        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_SUCCESS)

    @patch.object(lax_provider, 'article_snippet')
    def test_do_activity_no_lax_snippet(self, fake_snippet):
        fake_snippet.return_value = {}
        result = self.generatepdfcovers.do_activity(self.data)
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(lax_provider, 'article_snippet')
    def test_do_activity_no_subjects(self, fake_snippet):
        fake_snippet.return_value = {"status": "poa"}
        result = self.generatepdfcovers.do_activity(self.data)
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_SUCCESS)

    @patch.object(lax_provider, 'article_snippet')
    def test_do_activity_lax_exception(self, fake_snippet):
        fake_snippet.side_effect = Exception('Exception in Lax snippet GET request')
        result = self.generatepdfcovers.do_activity(self.data)
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)


if __name__ == '__main__':
    unittest.main()
