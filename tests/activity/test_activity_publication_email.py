# coding=utf-8

import os
import unittest
import shutil
from collections import OrderedDict
from testfixtures import TempDirectory
from mock import mock, patch
from ddt import ddt, data, unpack
from provider.templates import Templates
from provider.article import article
from provider.ejp import EJP
import activity.activity_PublicationEmail as activity_module
from activity.activity_PublicationEmail import activity_PublicationEmail
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
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "normal article with input_data None",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife03385.xml"],
            "article_id": "03385",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "basic PoA article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_1,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": "03977",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "Cannot build article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": True,
            "article_xml_filenames": ["does_not_exist.xml"],
            "article_id": None,
            "activity_success": self.activity.ACTIVITY_PERMANENT_FAILURE})

        self.do_activity_passes.append({
            "comment": "Not warmed templates",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": None,
            "templates_warmed": False,
            "article_xml_filenames": ["elife_poa_e03977.xml"],
            "article_id": None,
            "activity_success": self.activity.ACTIVITY_PERMANENT_FAILURE})

        self.do_activity_passes.append({
            "comment": "article-commentary with a related article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml"],
            "related_article": "tests/test_data/elife-15747-v2.xml",
            "article_id": "18753",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "article-commentary, related article cannot be found",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml"],
            "related_article": None,
            "article_id": "18753",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "article-commentary plus its matching insight",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-18753-v1.xml", "elife-15747-v2.xml"],
            "article_id": "18753",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "feature article",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-00353-v1.xml"],
            "article_id": "00353",
            "activity_success": True})

        self.do_activity_passes.append({
            "comment": "article-commentary with no related-article tag",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "input_data": {},
            "templates_warmed": True,
            "article_xml_filenames": ["elife-23065-v1.xml"],
            "article_id": "23065",
            "activity_success": True})

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

    @patch('provider.article.article.download_article_xml_from_s3')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('provider.lax_provider.article_versions')
    @patch.object(Templates, 'download_email_templates_from_s3')
    @patch.object(EJP, 'get_s3key')
    @patch.object(EJP, 'find_latest_s3_file_name')
    @patch.object(FakeStorageContext, 'list_resources')
    @patch('activity.activity_PublicationEmail.storage_context')
    def test_do_activity(self, fake_storage_context, fake_list_resources,
                         fake_find_latest_s3_file_name,
                         fake_ejp_get_s3key,
                         fake_download_email_templates,
                         fake_article_versions,
                         fake_email_smtp_connect,
                         fake_download_xml):

        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_xml.return_value = False

        # Basic fake data for all activity passes
        fake_ejp_get_s3key.return_value = fake_get_s3key(
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

            self.fake_download_email_templates_from_s3(
                self.activity.get_tmp_dir(), pass_test_data["templates_warmed"])

            fake_list_resources.return_value = pass_test_data["article_xml_filenames"]

            success = self.activity.do_activity(pass_test_data["input_data"])

            self.assertEqual(
                success, pass_test_data["activity_success"],
                'failed success check in {comment}'.format(
                    comment=pass_test_data.get("comment")))

            # reset object values
            self.activity.related_articles = []

    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_download_failure(self, fake_download_templates):
        fake_download_templates.side_effect = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_PublicationEmail, "process_articles")
    @patch.object(activity_PublicationEmail, "download_files_from_s3_outbox")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_process_articles_failure(
            self, fake_download_templates, fake_download_files, fake_process_articles):
        fake_download_templates.return_value = True
        fake_download_files.return_value = True
        fake_process_articles.side_effect = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_PublicationEmail, "send_emails_for_articles")
    @patch.object(activity_PublicationEmail, "process_articles")
    @patch.object(activity_PublicationEmail, "download_files_from_s3_outbox")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_process_send_emails_failure(
            self, fake_download_templates, fake_download_files,
            fake_process_articles, fake_send_emails):
        fake_download_templates.return_value = True
        fake_download_files.return_value = True
        fake_process_articles.return_value = None, [0], None
        fake_send_emails.return_value = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, True)

    @patch('provider.article.article.download_article_xml_from_s3')
    @patch('provider.lax_provider.article_versions')
    @data(
        (
            "article-commentary, related article cannot be found",
            ["tests/test_data/elife-18753-v1.xml"],
            1, 0,
            {
                '10.7554/eLife.18753': 'tests/test_data/elife-18753-v1.xml'
            }),
        (
            "article-commentary plus its matching insight",
            ["tests/test_data/elife-18753-v1.xml", "tests/test_data/elife-15747-v2.xml"],
            2, 1,
            {
                '10.7554/eLife.15747': 'tests/test_data/elife-15747-v2.xml',
                '10.7554/eLife.18753': 'tests/test_data/elife-18753-v1.xml'
            })
    )
    @unpack
    def test_process_articles(self, comment, xml_filenames, expected_approved, expected_prepared,
                              expected_map, fake_article_versions, fake_download_xml):
        """edge cases for process articles where the approved and prepared count differ"""
        fake_article_versions.return_value = (200, LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3)
        fake_download_xml.return_value = False
        approved, prepared, xml_file_to_doi_map = self.activity.process_articles(xml_filenames)
        self.assertEqual(
            len(approved), expected_approved,
            'failed expected_approved check in {comment}'.format(comment=comment))
        self.assertEqual(
            len(prepared), expected_prepared,
            'failed expected_prepared check in {comment}'.format(comment=comment))
        self.assertEqual(
            xml_file_to_doi_map, expected_map,
            'failed expected_map check in {comment}'.format(comment=comment))

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

        self.fake_download_email_templates_from_s3(self.activity.get_tmp_dir(), True)

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

        self.fake_download_email_templates_from_s3(self.activity.get_tmp_dir(), True)

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
        failed_authors.append({})
        # Object with e_mail as a blank string
        failed_authors.append({"e_mail": " "})
        # Object with e_mail as None
        failed_authors.append({"e_mail": None})

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
            self.assertEqual(recipient_authors[0]["first_nm"], expected_0_first_nm)
            self.assertEqual(recipient_authors[0]["e_mail"], expected_0_e_mail)


class TestGetRelatedArticle(unittest.TestCase):

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_related_article_from_cache(self):
        """get related article from existing list of related articles"""
        doi = "10.7554/eLife.15747"
        expected_doi = doi
        related_article = article()
        related_article.parse_article_file("tests/test_data/elife-15747-v2.xml")
        return_value = activity_module.get_related_article(
            settings_mock, TempDirectory(), doi, [related_article], FakeLogger(), "")
        self.assertEqual(return_value.doi, expected_doi)

    @patch("provider.article.create_article")
    def test_get_related_article_create_article(self, fake_create_article):
        """get related article from creating a new article for the doi"""
        doi = "10.7554/eLife.15747"
        expected_doi = doi
        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-15747-v2.xml")
        fake_create_article.return_value = article_object
        related_articles = []
        return_value = activity_module.get_related_article(
            settings_mock, TempDirectory(), doi, related_articles, FakeLogger(), "")
        self.assertEqual(return_value.doi, expected_doi)
        self.assertEqual(len(related_articles), 1)


class FakeArticle(object):
    def __init__(self, doi):
        self.doi = doi


@ddt
class TestS3KeyNamesToClean(unittest.TestCase):

    @data(
        {
            "comment": "blank inputs",
            "prepared": [],
            "xml_file_to_doi_map": {},
            "do_not_remove": [],
            "do_remove": [],
            "expected": []
        },
        {
            "comment": "normal clean one article",
            "prepared":
            [
                FakeArticle('1')
            ],
            "xml_file_to_doi_map":
            OrderedDict([
                ('1', '1.xml')
            ]),
            "do_not_remove": [],
            "do_remove": [],
            "expected":
            [
                'outbox/1.xml'
            ]
        },
        {
            "comment": "one article and do not clean it, by doi value",
            "prepared":
            [
                FakeArticle('1')
            ],
            "xml_file_to_doi_map":
            OrderedDict([
                ('1', '1.xml')
            ]),
            "do_not_remove":
            [
                '1'
            ],
            "do_remove": [],
            "expected": []
        },
        {
            "comment": "one article prepared, one insight, clean both",
            "prepared":
            [
                FakeArticle('1')
            ],
            "xml_file_to_doi_map":
            OrderedDict([
                ('1', '1.xml'),
                ('2', '2.xml')
            ]),
            "do_not_remove": [],
            "do_remove":
            [
                FakeArticle('2')
            ],
            "expected":
            [
                'outbox/1.xml',
                'outbox/2.xml'
            ]
        },
    )
    def test_s3_key_names_to_clean(self, test_data):
        """get related article from existing list of related articles"""
        s3_key_names = activity_module.s3_key_names_to_clean(
            "outbox/", test_data.get("prepared"), test_data.get("xml_file_to_doi_map"),
            test_data.get("do_not_remove"), test_data.get("do_remove"))
        self.assertEqual(
            s3_key_names, test_data.get("expected"),
            'failed check in {comment}'.format(comment=test_data.get("comment")))


def fake_get_s3key(directory, to_dir, document, source_doc):
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
