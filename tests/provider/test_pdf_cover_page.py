import unittest
from mock import patch
from provider import pdf_cover_page
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


class TestPdfCoverPage(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    @patch("requests.post")
    def test_get_pdf_cover_link(self, fake_post):
        article_id = 353
        formats = {
            "a4": "https://s3.example.org/bucket_name/00353-cover-a4.pdf",
            "letter": "https://s3.example.org/bucket_name/00353-cover-letter.pdf",
        }
        fake_post.return_value = FakeResponse(200, response_json={"formats": formats})
        return_value = pdf_cover_page.get_pdf_cover_link(
            settings_mock.pdf_cover_generator, article_id, self.logger
        )
        self.assertEqual(return_value, formats)

    def test_get_pdf_cover_page(self):
        article_id = "00353"
        expected = "https://localhost.org/download-your-cover/00353"
        return_value = pdf_cover_page.get_pdf_cover_page(
            article_id, settings_mock, self.logger
        )
        self.assertEqual(return_value, expected)

    def test_get_pdf_cover_page_exception(self):
        "test if settings is None, which does not contain pdf_cover_landing_page"
        article_id = "00353"
        return_value = pdf_cover_page.get_pdf_cover_page(article_id, None, self.logger)
        self.assertEqual(return_value, "")
        self.assertEqual(
            self.logger.logerror,
            "pdf_cover_landing_page variable is missing from settings file!",
        )
