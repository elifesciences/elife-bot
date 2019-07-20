# coding=utf-8

import os
import unittest
import shutil
from testfixtures import TempDirectory
from mock import mock, patch
from ddt import ddt, data, unpack
from provider.templates import Templates
from provider.article import article
from provider.ejp import EJP
import activity.activity_PublicationEmail as activity_module
from activity.activity_PublicationEmail import activity_PublicationEmail
from activity.activity_PublicationEmail import Struct
import tests.test_data as test_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.helpers import instantiate_article
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeKey, FakeStorageContext


LAX_ARTICLE_VERSIONS_RESPONSE_DATA_1 = test_data.lax_article_versions_response_data[:1]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_2 = test_data.lax_article_versions_response_data[:2]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3 = test_data.lax_article_versions_response_data[:3]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_4 = (
    test_data.lax_article_versions_response_data[:3] + [
        {
            "status": "vor",
            "version": 4,
            "published": "2015-11-26T00:00:00Z",
            "versionDate": "2015-12-30T00:00:00Z"
        }
    ])


def fake_authors(activity_object, article_id=3):
    return activity_object.get_authors(article_id, None, "tests/test_data/ejp_author_file.csv")


@ddt
class TestPublicationEmail(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(settings_mock, fake_logger, None, None, None)

        self.do_activity_passes = []

        self.do_activity_passes.append({
            "comment": "normal article with dict input_data",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife00013.xml"],
            "article_id": "00013",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "normal article with input_data None",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife03385.xml"],
            "article_id": "03385",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "basic PoA article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_1,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": "03977",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "not first version of PoA article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_2,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": "03977",
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        self.do_activity_passes.append({
            "comment": "not first version of VoR article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_4,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife03385.xml"],
            "article_id": "03385",
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        self.do_activity_passes.append({
            "comment": "Cannot build article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["does_not_exist.xml"],
            "article_id": None,
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        self.do_activity_passes.append({
            "comment": "Not warmed templates",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": False,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": None,
            "activity_success": True,
            "articles_approved_len": 0,
            "articles_approved_prepared_len": 0})

        self.do_activity_passes.append({
            "comment": "article-commentary with a related article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml"],
            "related_article": "tests/test_data/elife-15747-v2.xml",
            "article_id": "18753",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "article-commentary, related article cannot be found",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml"],
            "related_article": None,
            "article_id": "18753",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 0})

        self.do_activity_passes.append({
            "comment": "article-commentary plus its matching insight",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml", "elife-15747-v2.xml"],
            "article_id": "18753",
            "activity_success": True,
            "articles_approved_len": 2,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "feature article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-00353-v1.xml"],
            "article_id": "00353",
            "activity_success": True,
            "articles_approved_len": 1,
            "articles_approved_prepared_len": 1})

        self.do_activity_passes.append({
            "comment": "article-commentary with no related-article tag",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
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

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('provider.lax_provider.article_versions')
    @patch.object(Templates, 'download_email_templates_from_s3')
    @patch.object(article, 'get_folder_names_from_bucket')
    @patch.object(EJP, 'get_s3key')
    @patch.object(EJP, 'find_latest_s3_file_name')
    @patch.object(activity_PublicationEmail, 'clean_tmp_dir')
    @patch.object(FakeStorageContext, 'list_resources')
    @patch('activity.activity_PublicationEmail.storage_context')
    def test_do_activity(self, fake_storage_context, fake_list_resources, fake_clean_tmp_dir,
                         fake_find_latest_s3_file_name,
                         fake_ejp_get_s3key,
                         fake_article_get_folder_names,
                         fake_download_email_templates,
                         fake_article_versions,
                         fake_email_smtp_connect):

        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_storage_context.return_value = FakeStorageContext()

        # Basic fake data for all activity passes
        fake_article_get_folder_names.return_value = []
        fake_ejp_get_s3key.return_value = fake_ejp_get_s3key(
            directory, self.activity.get_tmp_dir(), "authors.csv",
            "tests/test_data/ejp_author_file.csv")
        fake_find_latest_s3_file_name.return_value = mock.MagicMock()
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())

        # do_activity
        for pass_test_data in self.do_activity_passes:

            # Prime the related article property for when needed
            if pass_test_data.get("related_article"):
                related_article = article()
                related_article.parse_article_file(pass_test_data.get("related_article"))
                self.activity.related_articles = [related_article]

            fake_article_versions.return_value = (
                200, pass_test_data.get("lax_article_versions_response_data"))

            fake_download_email_templates.return_value = (
                self.fake_download_email_templates_from_s3(
                    self.activity.get_tmp_dir(), pass_test_data["templates_warmed"]))

            fake_list_resources.return_value = pass_test_data["article_xml_filenames"]

            success = self.activity.do_activity(pass_test_data["input_data"])

            self.assertEqual(
                success, pass_test_data["activity_success"],
                'failed success check in {comment}'.format(
                    comment=pass_test_data.get("comment")))
            self.assertEqual(
                len(self.activity.articles_approved),
                pass_test_data["articles_approved_len"],
                'failed articles_approved_len check in {comment}'.format(
                    comment=pass_test_data.get("comment")))
            self.assertEqual(
                len(self.activity.articles_approved_prepared),
                pass_test_data["articles_approved_prepared_len"],
                'failed articles_approved_prepared_len check in {comment}'.format(
                    comment=pass_test_data.get("comment")))

            # reset related_articles
            self.activity.related_articles = []

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
        email_type = activity_module.choose_email_type(
            article_type, is_poa, was_ever_poa, feature_article)
        self.assertEqual(email_type, expected_email_type)


    @patch.object(Templates, 'download_email_templates_from_s3')
    def test_template_get_email_headers_00013(self, fake_download_email_templates):

        fake_download_email_templates.return_value = self.fake_download_email_templates_from_s3(
            self.activity.get_tmp_dir(), True)

        email_type = "author_publication_email_VOR_no_POA"

        authors = fake_authors(self.activity, 13)

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife00013.xml")
        article_type = article_object.article_type
        feature_article = False
        related_insight_article = None
        features_email = "features_team@example.org"

        recipient_authors = activity_module.choose_recipient_authors(
            authors, article_type, feature_article, related_insight_article, features_email)
        author = recipient_authors[2]

        email_format = "html"

        expected_headers = {
            'format': 'html',
            u'email_type': u'author_publication_email_VOR_no_POA',
            u'sender_email': u'press@elifesciences.org',
            u'subject': u'Authoré, Your eLife paper is now online'
            }

        body = self.activity.templates.get_email_headers(
            email_type=email_type,
            author=author,
            article=article_object,
            format=email_format)

        self.assertEqual(body, expected_headers)

    @patch.object(Templates, 'download_email_templates_from_s3')
    def test_template_get_email_body_00353(self, fake_download_email_templates):

        fake_download_email_templates.return_value = self.fake_download_email_templates_from_s3(
            self.activity.get_tmp_dir(), True)

        email_type = "author_publication_email_Feature"

        authors = fake_authors(self.activity)

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = "https://localhost.org/download-your-cover/00353"
        article_type = article_object.article_type
        feature_article = True
        related_insight_article = None
        features_email = "features_team@example.org"

        recipient_authors = activity_module.choose_recipient_authors(
            authors, article_type, feature_article, related_insight_article, features_email)
        author = recipient_authors[0]

        email_format = "html"

        expected_body = (
            'Header\n<p>Dear Features</p>\n"A good life"\n' +
            '<a href="https://doi.org/10.7554/eLife.00353">read it</a>\n' +
            '<a href="http://twitter.com/intent/tweet?text=https%3A%2F%2Fdoi.org%2F10.7554%2F' +
            'eLife.00353+%40eLife">social media</a>\n' +
            '<a href="https://lens.elifesciences.org/00353">online viewer</a>\n' +
            '<a href="https://localhost.org/download-your-cover/00353">pdf cover</a>\n\n' +
            'author01@example.com\n\nauthor02@example.org\n\nauthor03@example.com\n')

        body = self.activity.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article_object,
            authors=authors,
            format=email_format)

        self.assertEqual(body, expected_body)

    def test_get_pdf_cover_page(self):

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = article_object.get_pdf_cover_page(
            article_object.doi_id, self.activity.settings, self.activity.logger)
        self.assertEqual(article_object.pdf_cover_link,
                         "https://localhost.org/download-your-cover/00353")

    @patch.object(activity_PublicationEmail, 'send_author_email')
    def test_send_email_bad_authors(self, fake_send_author_email):
        fake_send_author_email.return_value = None
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
    def test_removes_articles_based_on_article_type(self, fake_article_versions):
        "test removing articles based on article type"
        fake_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        research_article_doi = '10.7554/eLife.99996'
        editorial_article = instantiate_article('editorial', '10.7554/eLife.99999')
        correction_article = instantiate_article('correction', '10.7554/eLife.99998')
        retraction_article = instantiate_article('retraction', '10.7554/eLife.99997')
        research_article = instantiate_article(
            'research-article', research_article_doi, False, True)
        articles = [editorial_article, correction_article, retraction_article, research_article]
        approved_articles = self.activity.approve_articles(articles)
        # one article will remain, the research-article
        self.assertEqual(len(approved_articles), 1)
        self.assertEqual(approved_articles[0].doi, research_article_doi)


@ddt
class TestChooseRecipientAuthors(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(settings_mock, fake_logger, None, None, None)

    @data(
        (None, None, None, "features_team@example.org",
         "Author", "author01@example.com"),
        (None, True, None, "features_team@example.org",
         "Features", "features_team@example.org"),
        (None, None, "not_none", "features_team@example.org",
         "Features", "features_team@example.org"),
        ("article-commentary", False, None, "features_team@example.org",
         "Features", "features_team@example.org"),
        ("article-commentary", False, None, ["features_team@example.org"],
         "Features", "features_team@example.org")
    )
    @unpack
    def test_choose_recipient_authors(self, article_type, feature_article, related_insight_article,
                                      features_email,
                                      expected_0_first_nm, expected_0_e_mail):
        authors = fake_authors(self.activity)
        recipient_authors = activity_module.choose_recipient_authors(
            authors, article_type, feature_article, related_insight_article, features_email)
        if recipient_authors:
            self.assertEqual(recipient_authors[0].first_nm, expected_0_first_nm)
            self.assertEqual(recipient_authors[0].e_mail, expected_0_e_mail)


def fake_ejp_get_s3key(directory, to_dir, document, source_doc):
    """
    EJP data do two things, copy the CSV file to where it should be
    and also set the fake S3 key object
    """
    dest_doc = os.path.join(to_dir, document)
    shutil.copy(source_doc, dest_doc)
    with open(source_doc, "rb") as open_file:
        return FakeKey(directory, document, open_file.read())


if __name__ == '__main__':
    unittest.main()
