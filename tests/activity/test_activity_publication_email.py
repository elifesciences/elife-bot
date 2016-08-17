import unittest
from activity.activity_PublicationEmail import activity_PublicationEmail
import shutil

from mock import mock, patch
import settings_mock
from classes_mock import FakeLogger
from ddt import ddt, data, unpack
import time

from provider.templates import Templates
from provider.article import article
from provider.ejp import EJP
from provider.simpleDB import SimpleDB

from classes_mock import FakeKey

from testfixtures import TempDirectory

import os
# Add parent directory for imports, so activity classes can use elife-poa-xml-generation
parentdir = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, parentdir)


@ddt
class TestPublicationEmail(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(settings_mock, fake_logger, None, None, None)

        self.do_activity_passes = []

        self.do_activity_passes.append({
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife00013.xml"],
            "article_id": "00013",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "input_data": {"data": {"allow_duplicates": True}},
            "templates_warmed": True,
            "article_xml_filenames": ["elife00013.xml"],
            "article_id": "00013",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "input_data": {"data": {"allow_duplicates": False}},
            "templates_warmed": True,
            "article_xml_filenames": ["elife03385.xml"],
            "article_id": "03385",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "input_data": {"data": {"allow_duplicates": False}},
            "templates_warmed": True,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": "03977",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        # Cannot build article
        self.do_activity_passes.append({
            "input_data": {"data": {"allow_duplicates": True}},
            "templates_warmed": True,
            "article_xml_filenames": ["does_not_exist.xml"],
            "article_id": None,
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        # Not warmed templates
        self.do_activity_passes.append({
            "input_data": {"data": {"allow_duplicates": True}},
            "templates_warmed": False,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": None,
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        # article-commentary
        self.do_activity_passes.append({
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml"],
            "article_id": "18753",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        # article-commentary plus its matching insight
        self.do_activity_passes.append({
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml", "elife-15747-v2.xml"],
            "article_id": "18753",
            "activity_success": True,
            "articles_approved_len": 2,
            "articles_approved_prepared_len": 1})




    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def fake_download_email_templates_from_s3(self, to_dir, templates_warmed):
        template_list = self.activity.templates.get_email_templates_list()
        for filename in template_list:
            source_doc = "tests/test_data/templates/" + filename
            dest_doc = os.path.join(to_dir, filename)
            shutil.copy(source_doc, dest_doc)
        self.activity.templates.email_templates_warmed = templates_warmed

    def fake_download_files_from_s3_outbox(self, xml_filenames, to_dir):
        xml_filename_paths = []
        for filename in xml_filenames:
            source_doc = "tests/test_data/" + filename
            dest_doc = os.path.join(to_dir, filename)
            try:
                shutil.copy(source_doc, dest_doc)
                xml_filename_paths.append(dest_doc)
            except IOError:
                pass
        return xml_filename_paths

    def fake_article_get_folder_names_from_bucket(self):
        return []

    def fake_ejp_get_s3key(self, directory, to_dir, document, source_doc):
        """
        EJP data do two things, copy the CSV file to where it should be
        and also set the fake S3 key object
        """
        dest_doc = os.path.join(to_dir, document)
        shutil.copy(source_doc, dest_doc)
        with open(source_doc, "rb") as fp:
            return FakeKey(directory, document, fp.read())

    def fake_clean_tmp_dir(self):
        """
        Disable the default clean_tmp_dir() when do_activity runs
        so tests can introspect the files first
        Then can run clean_tmp_dir() in the tearDown later
        """
        pass


    @patch.object(activity_PublicationEmail, 'download_files_from_s3_outbox')
    @patch.object(Templates, 'download_email_templates_from_s3')
    @patch.object(article, 'get_folder_names_from_bucket')
    @patch.object(article, 'check_is_article_published_by_lax')
    @patch.object(EJP, 'get_s3key')
    @patch.object(EJP, 'find_latest_s3_file_name')
    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    @patch.object(activity_PublicationEmail, 'clean_tmp_dir')
    def test_do_activity(self, fake_clean_tmp_dir, fake_elife_add_email_to_email_queue,
                         fake_find_latest_s3_file_name,
                         fake_ejp_get_s3key, 
                         fake_check_is_article_published_by_lax,
                         fake_article_get_folder_names_from_bucket,
                         fake_download_email_templates_from_s3,
                         fake_download_files_from_s3_outbox):

        directory = TempDirectory()
        fake_clean_tmp_dir = self.fake_clean_tmp_dir()

        # Prime the related article property for when needed
        related_article = article()
        related_article.parse_article_file("tests/test_data/elife-15747-v2.xml")
        self.activity.related_articles = [related_article]

        # Basic fake data for all activity passes
        fake_article_get_folder_names_from_bucket.return_value = self.fake_article_get_folder_names_from_bucket()
        fake_check_is_article_published_by_lax.return_value = True
        fake_ejp_get_s3key.return_value = self.fake_ejp_get_s3key(
            directory, self.activity.get_tmp_dir(), "authors.csv", "tests/test_data/ejp_author_file.csv")
        fake_find_latest_s3_file_name.return_value = mock.MagicMock()
        fake_elife_add_email_to_email_queue.return_value = mock.MagicMock()

        # do_activity
        for test_data in self.do_activity_passes:

            fake_download_email_templates_from_s3 = self.fake_download_email_templates_from_s3(
                self.activity.get_tmp_dir(), test_data["templates_warmed"])

            fake_download_files_from_s3_outbox.return_value = self.fake_download_files_from_s3_outbox(
                test_data["article_xml_filenames"], self.activity.get_tmp_dir())


            success = self.activity.do_activity(test_data["input_data"])

            self.assertEqual(True, test_data["activity_success"])
            self.assertEqual(len(self.activity.articles_approved), test_data["articles_approved_len"])
            self.assertEqual(len(self.activity.articles_approved_prepared), test_data["articles_approved_prepared_len"])


    @data(
        (3, "tests/test_data/ejp_editor_file.csv", 1, "One"),
        ("00013", "tests/test_data/ejp_editor_file.csv", 1, "Uno"),
        (666, "tests/test_data/ejp_editor_file.csv", 0, None)
    )
    @unpack
    def test_get_editors(self, doi_id, document, expected_editor_list_len, expected_0_last_nm):
        editor_list = self.activity.get_editors(doi_id, document)
        if editor_list:
            self.assertEqual(len(editor_list), expected_editor_list_len)
        else:
            self.assertEqual(editor_list, None)

        if expected_0_last_nm:
            self.assertEqual(editor_list[0].last_nm, expected_0_last_nm)




if __name__ == '__main__':
    unittest.main()
