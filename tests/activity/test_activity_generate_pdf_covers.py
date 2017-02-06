import unittest
from activity.activity_GeneratePDFCovers import activity_GeneratePDFCovers
import settings_mock
from classes_mock import FakeLogger
from classes_mock import FakeResponse
from mock import patch
from provider.article import article

class TestGeneratePDFCovers(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.generatepdfcovers = activity_GeneratePDFCovers(settings_mock, self.fake_logger, None, None, None)

    def test_do_activity_bad_data(self):
        data = None
        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(self.fake_logger.logerror[:36], "Error retrieving basic article data.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)

    @patch('requests.get')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_404(self, fake_monitor_event, fake_request):
        data = {"run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
                "article_id": "00353",
                "version": "1"}
        fake_request.return_value = FakeResponse(404, {})

        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(self.fake_logger.logerror[:20], "PDF cover not found.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)

    @patch('requests.get')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_500(self, fake_monitor_event, fake_request):
        data = {"run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
                "article_id": "00353",
                "version": "1"}
        fake_request.return_value = FakeResponse(500, {})

        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(self.fake_logger.logerror[:44], "unhandled status code from PDF cover service")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(article, 'get_pdf_cover_link')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_error_wrong_result_from_covers(self, fake_monitor_event, fake_article_pdf_cover_link):
        data = {"run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
                "article_id": "00353",
                "version": "1"}
        fake_article_pdf_cover_link.return_value = ""

        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(self.fake_logger.logerror[:44], "Unexpected result from pdf covers API.")
        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_PERMANENT_FAILURE)

    @patch('requests.get')
    @patch.object(activity_GeneratePDFCovers, 'emit_monitor_event')
    def test_do_activity_success(self, fake_monitor_event, fake_request):
        data = {"run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
                "article_id": "00353",
                "version": "1"}
        fake_request.return_value = FakeResponse(200, {"cover":"https://s3.eu-west-2.amazonaws.com/elifecoversht/09560"})

        result = self.generatepdfcovers.do_activity(data)

        self.assertEqual(result, self.generatepdfcovers.ACTIVITY_SUCCESS)



if __name__ == '__main__':
    unittest.main()
