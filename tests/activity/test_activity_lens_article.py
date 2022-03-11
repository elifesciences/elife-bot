import unittest
import os
import shutil
from mock import patch
from activity.activity_LensArticle import activity_LensArticle
from provider.article import article
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data


def fake_download_xml(filename, to_dir):
    source_doc = "tests/test_data/" + filename
    dest_doc = os.path.join(to_dir, filename)
    try:
        shutil.copy(source_doc, dest_doc)
        return filename
    except IOError:
        pass
    # default return assume a failure
    return False


class TestLensArticle(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_LensArticle(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        helpers.delete_files_in_folder(
            test_activity_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )
        self.activity.clean_tmp_dir()

    @patch("activity.activity_LensArticle.storage_context")
    @patch.object(article, "download_article_xml_from_s3")
    def test_do_activity(self, fake_download_article_xml, fake_storage_context):
        input_data = {"article_id": "353"}
        article_xml_file = "elife-00353-v1.xml"
        article_s3key = "00353/index.html"
        expected_html_contains = (
            "https://cdn.elifesciences.org/articles/00353/elife-00353-v1.xml"
        )

        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext()

        success = self.activity.do_activity(input_data)
        self.assertEqual(success, True)
        self.assertEqual(article_xml_file, self.activity.article_xml_filename)
        self.assertEqual(article_s3key, self.activity.article_s3key)
        self.assertTrue(expected_html_contains in self.activity.article_html)
        self.assertIsNotNone(self.activity.article_html)

    @patch.object(article, "download_article_xml_from_s3")
    def test_do_activity_no_article_xml_filename(self, fake_download_article_xml):
        "for test coverage if an article XML file is not found"
        input_data = {"article_id": "353"}
        fake_download_article_xml.return_value = None
        success = self.activity.do_activity(input_data)
        self.assertEqual(success, True)

    @patch("activity.activity_LensArticle.storage_context")
    @patch.object(article, "download_article_xml_from_s3")
    def test_do_activity_poa_article(
        self, fake_download_article_xml, fake_storage_context
    ):
        "for test coverage try a POA article"
        input_data = {"article_id": "3977"}
        article_xml_file = "elife_poa_e03977.xml"
        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext()

        success = self.activity.do_activity(input_data)
        self.assertEqual(success, True)

    def test_get_article_html(self):
        "test coverage of passing None"
        article_html = self.activity.get_article_html(None, None, None, None)
        self.assertIsNotNone(article_html)
