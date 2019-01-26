# coding=utf-8

import os
import unittest
import time
import shutil
from testfixtures import TempDirectory
from mock import mock, patch
from ddt import ddt, data, unpack
from provider.templates import Templates
from provider.article import article
from provider.ejp import EJP
from provider.simpleDB import SimpleDB
from activity.activity_PublicationEmail import activity_PublicationEmail
from activity.activity_PublicationEmail import Struct
import tests.test_data as test_data
from tests.activity.helpers import instantiate_article
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeKey


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

        # feature article
        self.do_activity_passes.append({
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-00353-v1.xml"],
            "article_id": "00353",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        # article-commentary with no related-article tag
        self.do_activity_passes.append({
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-23065-v1.xml"],
            "article_id": "23065",
            "activity_success": True,
            "articles_approved_len": 1,
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

    @patch('provider.lax_provider.article_versions')
    @patch.object(activity_PublicationEmail, 'download_files_from_s3_outbox')
    @patch.object(Templates, 'download_email_templates_from_s3')
    @patch.object(article, 'get_folder_names_from_bucket')
    @patch.object(EJP, 'get_s3key')
    @patch.object(EJP, 'find_latest_s3_file_name')
    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    @patch.object(activity_PublicationEmail, 'clean_tmp_dir')
    def test_do_activity(self, fake_clean_tmp_dir, fake_elife_add_email_to_email_queue,
                         fake_find_latest_s3_file_name,
                         fake_ejp_get_s3key,
                         fake_article_get_folder_names_from_bucket,
                         fake_download_email_templates_from_s3,
                         fake_download_files_from_s3_outbox,
                         mock_lax_provider_article_versions):

        directory = TempDirectory()
        fake_clean_tmp_dir = self.fake_clean_tmp_dir()

        # Prime the related article property for when needed
        related_article = article()
        related_article.parse_article_file("tests/test_data/elife-15747-v2.xml")
        self.activity.related_articles = [related_article]

        # Basic fake data for all activity passes
        fake_article_get_folder_names_from_bucket.return_value = self.fake_article_get_folder_names_from_bucket()
        fake_ejp_get_s3key.return_value = self.fake_ejp_get_s3key(
            directory, self.activity.get_tmp_dir(), "authors.csv", "tests/test_data/ejp_author_file.csv")
        fake_find_latest_s3_file_name.return_value = mock.MagicMock()
        fake_elife_add_email_to_email_queue.return_value = mock.MagicMock()
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data

        # do_activity
        for pass_test_data in self.do_activity_passes:

            fake_download_email_templates_from_s3 = self.fake_download_email_templates_from_s3(
                self.activity.get_tmp_dir(), pass_test_data["templates_warmed"])

            fake_download_files_from_s3_outbox.return_value = self.fake_download_files_from_s3_outbox(
                pass_test_data["article_xml_filenames"], self.activity.get_tmp_dir())


            success = self.activity.do_activity(pass_test_data["input_data"])

            self.assertEqual(success, pass_test_data["activity_success"])
            self.assertEqual(len(self.activity.articles_approved), pass_test_data["articles_approved_len"])
            self.assertEqual(len(self.activity.articles_approved_prepared), pass_test_data["articles_approved_prepared_len"])


    @data(
        (3, "tests/test_data/ejp_editor_file.csv", 1, "One"),
        ("00013", "tests/test_data/ejp_editor_file.csv", 1, "Uno"),
        (666, "tests/test_data/ejp_editor_file.csv", 0, None)
    )
    @unpack
    def test_get_editors(self, doi_id, local_document, expected_editor_list_len, expected_0_last_nm):
        editor_list = self.activity.get_editors(doi_id, local_document)
        if editor_list:
            self.assertEqual(len(editor_list), expected_editor_list_len)
        else:
            self.assertEqual(editor_list, None)

        if expected_0_last_nm:
            self.assertEqual(editor_list[0].last_nm, expected_0_last_nm)

    @data(
        ("article-commentary", None, None, False, "author_publication_email_Insight_to_VOR"),
        ("discussion", None, None, True, "author_publication_email_Feature"),
        ("research-article", True, None, False, "author_publication_email_POA"),
        ("research-article", False, None, False, "author_publication_email_VOR_no_POA"),
        ("research-article", False, False, False, "author_publication_email_VOR_no_POA"),
        ("research-article", False, True, False, "author_publication_email_VOR_after_POA")
    )
    @unpack
    def test_choose_email_type(self, article_type, is_poa, was_ever_poa,
                               feature_article, expected_email_type):
        email_type = self.activity.choose_email_type(article_type, is_poa,
                                                     was_ever_poa, feature_article)
        self.assertEqual(email_type, expected_email_type)

    def fake_authors(self, article_id=3):
        return self.activity.get_authors(article_id, None, "tests/test_data/ejp_author_file.csv")


    @data(
        (None, None, None, "Author", "author01@example.com"),
        (None, True, None, "Features", "features_team@example.org"),
        (None, None, "not_none", "Features", "features_team@example.org"),
        ("article-commentary", False, None, "Features", "features_team@example.org")
    )
    @unpack
    def test_choose_recipient_authors(self, article_type, feature_article, related_insight_article,
                                      expected_0_first_nm, expected_0_e_mail):
        authors = self.fake_authors()
        recipient_authors = self.activity.choose_recipient_authors(authors, article_type,
                                                                   feature_article, related_insight_article)
        if recipient_authors:
            self.assertEqual(recipient_authors[0].first_nm, expected_0_first_nm)
            self.assertEqual(recipient_authors[0].e_mail, expected_0_e_mail)


    @patch.object(Templates, 'download_email_templates_from_s3')
    def test_template_get_email_headers_00013(self, fake_download_email_templates_from_s3):

        fake_download_email_templates_from_s3 = self.fake_download_email_templates_from_s3(
            self.activity.get_tmp_dir(), True)

        email_type = "author_publication_email_VOR_no_POA"

        authors = self.fake_authors(13)

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife00013.xml")
        article_type = article_object.article_type
        feature_article = False
        related_insight_article = None

        recipient_authors = self.activity.choose_recipient_authors(authors, article_type,
                                                                   feature_article, related_insight_article)
        author = recipient_authors[2]

        format = "html"

        expected_headers = {'format': 'html', u'email_type': u'author_publication_email_VOR_no_POA', u'sender_email': u'press@elifesciences.org', u'subject': u'Authoré, Your eLife paper is now online'}

        body = self.activity.templates.get_email_headers(
            email_type=email_type,
            author=author,
            article=article_object,
            format=format)

        self.assertEqual(body, expected_headers)



    @patch.object(Templates, 'download_email_templates_from_s3')
    def test_template_get_email_body_00353(self, fake_download_email_templates_from_s3):

        fake_download_email_templates_from_s3 = self.fake_download_email_templates_from_s3(
            self.activity.get_tmp_dir(), True)

        email_type = "author_publication_email_Feature"

        authors = self.fake_authors()

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = "https://localhost.org/download-your-cover/00353"
        article_type = article_object.article_type
        feature_article = True
        related_insight_article = None

        recipient_authors = self.activity.choose_recipient_authors(authors, article_type,
                                                                   feature_article, related_insight_article)
        author = recipient_authors[0]

        format = "html"

        expected_body = 'Header\n<p>Dear Features</p>\n"A good life"\n<a href="https://doi.org/10.7554/eLife.00353">read it</a>\n<a href="http://twitter.com/intent/tweet?text=https%3A%2F%2Fdoi.org%2F10.7554%2FeLife.00353+%40eLife">social media</a>\n<a href="https://lens.elifesciences.org/00353">online viewer</a>\n<a href="https://localhost.org/download-your-cover/00353">pdf cover</a>\n\nauthor01@example.com\n\nauthor02@example.org\n\nauthor03@example.com\n'

        body = self.activity.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article_object,
            authors=authors,
            format=format)

        self.assertEqual(body, expected_body)

    def test_get_pdf_cover_page(self):

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = article_object.get_pdf_cover_page(article_object.doi_id, self.activity.settings, self.activity.logger)
        self.assertEqual(article_object.pdf_cover_link, "https://localhost.org/download-your-cover/00353")


    @patch.object(activity_PublicationEmail, 'queue_author_email')
    def test_send_email_bad_authors(self, fake_queue_author_email):

        failed_authors = []
        # None
        failed_authors.append(None)
        # Object with no e_mail
        failed_authors.append(Struct())
        # Object with e_mail as a blank string
        failed_authors.append(Struct(**{"e_mail": " "}))
        # Object with e_mail as None
        failed_authors.append(Struct(**{"e_mail": None}))

        for failed_author in failed_authors:
            result = self.activity.send_email(None, None, failed_author, None, None)
            self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_removes_articles_based_on_article_type(self, mock_lax_provider_article_versions):
        "test removing articles based on article type"
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        research_article_doi = '10.7554/eLife.99996'
        editorial_article = instantiate_article('editorial', '10.7554/eLife.99999')
        correction_article = instantiate_article('correction', '10.7554/eLife.99998')
        retraction_article = instantiate_article('retraction', '10.7554/eLife.99997')
        research_article = instantiate_article('research-article', research_article_doi, True, True)
        articles = [editorial_article, correction_article, retraction_article, research_article]
        approved_articles = self.activity.approve_articles(articles)
        # one article will remain, the research-article
        self.assertEqual(len(approved_articles), 1)
        self.assertEqual(approved_articles[0].doi, research_article_doi)


if __name__ == '__main__':
    unittest.main()
