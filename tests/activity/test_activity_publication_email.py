# coding=utf-8

import os
import unittest
import shutil
import smtplib
from collections import OrderedDict
from testfixtures import TempDirectory
from mock import patch
from ddt import ddt, data, unpack
from provider import ejp, pdf_cover_page
from provider.templates import Templates
import provider.article as articlelib
from provider.ejp import EJP
import activity.activity_PublicationEmail as activity_module
from activity.activity_PublicationEmail import (
    activity_PublicationEmail,
    EmailRecipientException,
    EmailSendException,
    EmailTemplateException,
)
from tests import test_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data


LAX_ARTICLE_VERSIONS_RESPONSE_DATA_1 = test_data.lax_article_versions_response_data[:1]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_2 = test_data.lax_article_versions_response_data[:2]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3 = test_data.lax_article_versions_response_data[:3]
LAX_ARTICLE_VERSIONS_RESPONSE_DATA_4 = test_data.lax_article_versions_response_data[
    :3
] + [
    {
        "status": "vor",
        "version": 4,
        "published": "2015-11-26T00:00:00Z",
        "versionDate": "2015-12-30T00:00:00Z",
    }
]

DO_ACTIVITY_PASSES = []

DO_ACTIVITY_PASSES.append(
    {
        "comment": "normal article with dict input_data",
        "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
        "input_data": {},
        "article_xml_filenames": ["elife00013.xml"],
        "article_id": "13",
        "activity_success": True,
        "admin_email_content_contains": [
            "Parsed https://doi.org/10.7554/eLife.00013",
            "Total prepared articles: 1",
            (
                "Sending author_publication_email_VOR_after_POA type email "
                "for article 00013 to recipient_email author13-01@example.com"
            ),
        ],
    }
)


def fake_authors(activity_object, article_id=3):
    # parse author csv file or create test fixture data
    column_headings, authors = ejp.author_detail_list(
        "tests/test_data/ejp_author_file.csv", article_id
    )
    return activity_object.get_author_list(column_headings, authors, article_id)


def fake_preprint_authors(activity_object, article_id=3):
    # parse preprint author csv file or create test fixture data
    column_headings, authors = ejp.author_detail_list(
        "tests/test_data/ejp_preprint_author_file.csv", article_id
    )
    return activity_object.get_author_list(column_headings, authors, article_id)


# author test fixture data
EJP_ARTICLE_13_AUTHORS = (
    [
        "ms_no",
        "author_seq",
        "first_nm",
        "last_nm",
        "author_type_cde",
        "dual_corr_author_ind",
        "e_mail",
        "primary_org",
    ],
    [
        [
            "13",
            "1",
            "Author",
            "Uno",
            "Contributing Author",
            "",
            "author13-01@example.com",
            "University ",
        ]
    ],
)

# preprint article author test fixture data
EJP_ARTICLE_91826_AUTHORS = (
    [
        "ms_no",
        "ms_rev_no",
        "appeal_ind",
        "author_seq",
        "first_nm",
        "last_nm",
        "author_type_cde",
        "dual_corr_author_ind",
        "e_mail",
        "primary_org",
    ],
    [
        [
            "91826",
            "1",
            "",
            "1",
            "Author",
            "Uno",
            "Contributing Author",
            "",
            "author91826-01@example.com",
            "University ",
        ]
    ],
)


class TestPublicationEmail(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        # reduce the sleep time to speed up test runs
        activity_module.SLEEP_SECONDS = 0.001
        activity_module.MAX_EMAILS_PER_SECOND = 1000
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()
        helpers.delete_files_in_folder(
            test_activity_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_PublicationEmail, "process_articles")
    @patch.object(EJP, "get_authors")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity(
        self,
        fake_storage_context,
        fake_ejp_get_authors,
        fake_process_articles,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()
        prepared_article_xml_filenames = ["elife00013.xml", "elife03385.xml"]
        approved_article_xml_filenames = ["elife00013.xml"]
        not_published_article_xml_filenames = ["elife03385.xml"]
        expected_result = True

        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        storage_path = "tests/files_source/publication_email/outbox/"

        fake_storage_context.return_value = FakeStorageContext(
            storage_path,
            resources=prepared_article_xml_filenames,
        )

        fake_ejp_get_authors.return_value = EJP_ARTICLE_13_AUTHORS

        # Mock process_articles return values
        prepared, xml_file_to_doi_map = self.activity.parse_article_xml(
            [
                os.path.join(storage_path, xml_file)
                for xml_file in prepared_article_xml_filenames
            ]
        )
        approved = self.activity.parse_article_xml(
            [
                os.path.join(storage_path, xml_file)
                for xml_file in approved_article_xml_filenames
            ]
        )[0]
        not_published_articles = self.activity.parse_article_xml(
            [
                os.path.join(storage_path, xml_file)
                for xml_file in not_published_article_xml_filenames
            ]
        )[0]

        fake_process_articles.return_value = (
            approved,
            prepared,
            not_published_articles,
            xml_file_to_doi_map,
        )

        # invoke
        success = self.activity.do_activity()

        # assert
        self.assertEqual(success, expected_result)

    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_download_failure(
        self, fake_download_templates, fake_outbox_key_names
    ):
        fake_download_templates.return_value = False
        fake_outbox_key_names.return_value = []
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch.object(Templates, "copy_email_templates")
    def test_do_activity_download_templates_exception(
        self, fake_copy_email_templates, fake_outbox_key_names
    ):
        fake_copy_email_templates.side_effect = Exception("Something went wrong!")
        fake_outbox_key_names.return_value = []
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("provider.outbox_provider.download_files_from_s3_outbox")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_download_articles_exception(
        self, fake_download_templates, fake_outbox_key_names, fake_download_files
    ):
        fake_download_templates.return_value = True
        fake_outbox_key_names.return_value = ["elife00013.xml"]
        fake_download_files.side_effect = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_PublicationEmail, "process_articles")
    @patch("provider.outbox_provider.download_files_from_s3_outbox")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_process_articles_failure(
        self,
        fake_download_templates,
        fake_outbox_key_names,
        fake_download_files,
        fake_process_articles,
    ):
        fake_download_templates.return_value = True
        fake_download_files.return_value = True
        fake_outbox_key_names.return_value = ["elife00013.xml"]
        fake_process_articles.side_effect = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_PublicationEmail, "send_and_clean")
    @patch.object(activity_PublicationEmail, "process_articles")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_process_send_emails_failure(
        self,
        fake_download_templates,
        fake_storage_context,
        fake_process_articles,
        fake_send_and_clean,
    ):
        fake_download_templates.return_value = True
        fake_storage_context.return_value = FakeStorageContext(
            "tests/files_source/publication_email/outbox/",
            resources=[],
        )
        fake_process_articles.return_value = None, [0], [0], None
        fake_send_and_clean.return_value = Exception("Something went wrong!")
        result = self.activity.do_activity()
        self.assertEqual(result, True)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_PublicationEmail, "process_articles")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_PublicationEmail, "download_templates")
    def test_do_activity_not_prepared(
        self,
        fake_download_templates,
        fake_storage_context,
        fake_process_articles,
        fake_email_smtp_connect,
    ):
        "test if no prepared or not published articles are produced"
        directory = TempDirectory()
        fake_download_templates.return_value = True
        fake_storage_context.return_value = FakeStorageContext(
            "tests/files_source/publication_email/outbox/",
            resources=[],
        )
        fake_process_articles.return_value = [], [], [], None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        result = self.activity.do_activity()
        self.assertEqual(result, True)


class TestDownloadTemplates(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(Templates, "copy_email_templates")
    def test_download_templates_failure(self, fake_copy_email_templates):
        fake_copy_email_templates.return_value = False
        result = self.activity.download_templates()
        self.assertFalse(result)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "PublicationEmail email templates did not warm successfully",
        )


class TestSendAndClean(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, self.logger, None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch.object(EJP, "get_authors")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.outbox_provider.storage_context")
    def test_send_and_clean(
        self, fake_storage_context, fake_email_smtp_connect, fake_ejp_get_authors
    ):
        "test sending email, cleaning the outbox, sending admin email"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        article_xml_filenames = ["elife-18753-v1.xml", "elife-15747-v2.xml"]
        # copy XML files for testing
        storage_path = os.path.join(directory.path, "publication_email", "outbox")
        xml_path = os.path.join("tests", "files_source", "publication_email", "outbox")
        os.makedirs(storage_path)
        for article_xml in article_xml_filenames:
            copy_from = os.path.join(xml_path, article_xml)
            copy_to = os.path.join(storage_path, article_xml)
            shutil.copy(
                copy_from,
                copy_to,
            )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path,
            resources=article_xml_filenames,
            dest_folder=directory.path,
        )
        fake_ejp_get_authors.return_value = EJP_ARTICLE_13_AUTHORS
        # turn XML into article objects
        article_xml_paths = [
            os.path.join(storage_path, xml_file) for xml_file in article_xml_filenames
        ]
        articles, xml_file_to_doi_map = self.activity.parse_article_xml(
            article_xml_paths
        )
        prepared = [articles[0]]
        not_published_articles = articles[1:]
        # invoke
        self.activity.download_templates()
        self.activity.send_and_clean(
            prepared, not_published_articles, xml_file_to_doi_map
        )
        # assert outbox is empty
        self.assertEqual([], os.listdir(storage_path))

    @patch.object(EJP, "get_authors")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.outbox_provider.storage_context")
    def test_send_and_clean_no_ejp_authors(
        self, fake_storage_context, fake_email_smtp_connect, fake_ejp_get_authors
    ):
        "test sending email, cleaning the outbox, sending admin email"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        article_xml_filenames = ["elife-32991-v2.xml"]
        # copy XML files for testing
        storage_path = os.path.join(directory.path, "publication_email", "outbox")
        xml_path = os.path.join("tests", "files_source", "publication_email", "outbox")
        os.makedirs(storage_path)
        for article_xml in article_xml_filenames:
            copy_from = os.path.join(xml_path, article_xml)
            copy_to = os.path.join(storage_path, article_xml)
            shutil.copy(
                copy_from,
                copy_to,
            )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path,
            resources=article_xml_filenames,
            dest_folder=directory.path,
        )
        fake_ejp_get_authors.return_value = (None, None)
        # turn XML into article objects
        article_xml_paths = [
            os.path.join(storage_path, xml_file) for xml_file in article_xml_filenames
        ]
        articles, xml_file_to_doi_map = self.activity.parse_article_xml(
            article_xml_paths
        )
        prepared = [articles[0]]
        not_published_articles = articles[1:]
        # invoke
        self.activity.download_templates()
        self.activity.send_and_clean(
            prepared, not_published_articles, xml_file_to_doi_map
        )
        # assert outbox is empty
        self.assertEqual([], os.listdir(storage_path))
        # assert admin email content
        admin_email_content_contains = [
            "Parsed https://doi.org/10.7554/eLife.32991",
            "No authors found for article doi id 32991",
            (
                "Sending author_publication_email_VOR_no_POA type email for "
                "article 32991 to recipient_email alhonore@hotmail.com"
            ),
            "Adding alhonore@hotmail.com from additional",
        ]
        for expected in admin_email_content_contains:
            self.assertTrue(
                expected in self.activity.admin_email_content,
                "{expected} not found in admin_email_content".format(
                    expected=expected,
                ),
            )


class TestSendEmailsForArticles(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, self.logger, None, None, None
        )
        # abbreviated author data for testing
        self.authors = [
            {
                "e_mail": "author13-01@example.com",
            }
        ]
        articles, xml_file_to_doi_map = self.activity.parse_article_xml(
            ["tests/files_source/publication_email/outbox/elife00013.xml"]
        )
        self.articles = articles

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_PublicationEmail, "article_authors_by_article_type")
    def test_send_emails_for_articles_no_recipients(
        self,
        fake_article_authors,
    ):
        "test if there are no recipients"
        fake_article_authors.return_value = []
        # invoke the function
        self.activity.send_emails_for_articles(self.articles)
        # assertions
        self.assertEqual(
            self.logger.loginfo[-1],
            "Leaving article in the outbox because we cannot find its authors: 10.7554/eLife.00013",
        )

    @patch.object(activity_PublicationEmail, "send_email")
    @patch.object(activity_PublicationEmail, "article_authors_by_article_type")
    def test_send_emails_for_articles_send_email_recipient_exception(
        self,
        fake_article_authors,
        fake_send_email,
    ):
        "test if and email recipient raises and exception"
        fake_send_email.side_effect = EmailRecipientException("An exception")
        fake_article_authors.return_value = self.authors
        # invoke the function
        self.activity.send_emails_for_articles(self.articles)
        # assertions
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "Failed to send email for article 10.7554/eLife.00013 to recipient "
                "{'e_mail': 'author13-01@example.com'}"
            ),
        )

    @patch.object(Templates, "get_email_headers")
    @patch.object(activity_PublicationEmail, "article_authors_by_article_type")
    def test_send_emails_for_articles_send_email_template_exception(
        self,
        fake_article_authors,
        fake_get_email_headers,
    ):
        "test if rendering template headers raises an exception"
        fake_get_email_headers.side_effect = EmailTemplateException("An exception")
        fake_article_authors.return_value = self.authors
        # invoke the function
        self.activity.send_emails_for_articles(self.articles)
        # assertions
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "Failed to send email for article 10.7554/eLife.00013 to recipient "
                "{'e_mail': 'author13-01@example.com'}"
            ),
        )

    @patch.object(activity_PublicationEmail, "send_author_email")
    @patch.object(Templates, "get_email_headers")
    @patch.object(activity_PublicationEmail, "article_authors_by_article_type")
    def test_send_emails_for_articles_send_email_exception(
        self,
        fake_article_authors,
        fake_get_email_headers,
        fake_send_author_email,
    ):
        "test if sending an email raises an exception"
        fake_send_author_email.side_effect = EmailSendException("An exception")
        fake_get_email_headers.return_value = True
        fake_article_authors.return_value = self.authors
        # invoke the function
        self.activity.send_emails_for_articles(self.articles)
        # assertions
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "Failed to send email for article 10.7554/eLife.00013 to recipient "
                "{'e_mail': 'author13-01@example.com'}"
            ),
        )
        self.assertEqual(
            self.logger.logexception, "An error has occurred on send_email method"
        )


@ddt
class TestProcessArticles(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(EJP, "get_authors")
    @patch.object(activity_module, "get_related_article")
    @patch("provider.article.article.download_article_xml_from_s3")
    @patch("provider.lax_provider.article_versions")
    @data(
        {
            "comment": "normal article example",
            "xml_filenames": ["elife00013.xml"],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 1,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.00013",
                "Total prepared articles: 1",
            ],
        },
        {
            "comment": "basic PoA article",
            "xml_filenames": ["elife_poa_e03977.xml"],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_1,
            "expected_approved_count": 1,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.03977",
                "Total prepared articles: 1",
            ],
        },
        {
            "comment": "article-commentary with a related article",
            "xml_filenames": ["elife-18753-v1.xml"],
            "related_article": "tests/test_data/elife-15747-v2.xml",
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 1,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.18753",
                "Total prepared articles: 1",
            ],
        },
        {
            "comment": "article-commentary, related article cannot be found",
            "xml_filenames": ["elife-18753-v1.xml"],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 1,
            "expected_prepared_count": 0,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.18753",
                "Total parsed articles: 1",
                "Total approved articles: 1",
                "Total prepared articles: 0",
                "Total not published articles: 0",
            ],
        },
        {
            "comment": "article-commentary plus its matching insight",
            "xml_filenames": [
                "elife-18753-v1.xml",
                "elife-15747-v2.xml",
            ],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 2,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.18753",
                "Parsed https://doi.org/10.7554/eLife.15747",
                "Total parsed articles: 2",
                "Total approved articles: 2",
                "Total prepared articles: 1",
                "Total not published articles: 0",
            ],
        },
        {
            "comment": "feature article",
            "xml_filenames": [
                "elife-00353-v1.xml",
            ],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 1,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.00353",
                "Total prepared articles: 1",
            ],
        },
        {
            "comment": "article-commentary with no related-article tag",
            "xml_filenames": [
                "elife-23065-v1.xml",
            ],
            "lax_article_versions_response_data": LAX_ARTICLE_VERSIONS_RESPONSE_DATA_3,
            "expected_approved_count": 1,
            "expected_prepared_count": 0,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.23065",
                "Could not build the article related to insight 10.7554/eLife.23065",
                "Total approved articles: 1",
                "Total prepared articles: 0",
            ],
        },
        {
            "comment": "preprint article",
            "xml_filenames": [
                "elife-preprint-91826-v2.xml",
            ],
            "lax_article_versions_response_data": [{}],
            "expected_approved_count": 1,
            "expected_prepared_count": 1,
            "expected_not_published_count": 0,
            "admin_email_content_contains": [
                "Parsed https://doi.org/10.7554/eLife.91826",
                "Total parsed articles: 1",
                "Total approved articles: 1",
                "Total prepared articles: 1",
            ],
        },
    )
    def test_process_articles(
        self,
        test_case_data,
        fake_article_versions,
        fake_download_xml,
        fake_get_related_article,
        fake_ejp_get_authors,
    ):
        "edge cases for process articles where the approved and prepared count differ"
        fake_article_versions.return_value = (
            200,
            test_case_data.get("lax_article_versions_response_data"),
        )
        fake_download_xml.return_value = False

        if test_case_data.get("related_article"):
            related_article = articlelib.article()
            related_article.parse_article_file(test_case_data.get("related_article"))
            fake_get_related_article.return_value = related_article
        else:
            fake_get_related_article.return_value = None

        fake_ejp_get_authors.return_value = EJP_ARTICLE_13_AUTHORS

        xml_filename_paths = [
            os.path.join(
                "tests", "files_source", "publication_email", "outbox", xml_filename
            )
            for xml_filename in test_case_data.get("xml_filenames")
        ]
        (
            approved,
            prepared,
            not_published_articles,
            xml_file_to_doi_map,
        ) = self.activity.process_articles(xml_filename_paths)
        self.assertEqual(
            len(approved),
            test_case_data.get("expected_approved_count"),
            "failed expected_approved check in {comment}".format(
                comment=test_case_data.get("comment")
            ),
        )
        self.assertEqual(
            len(prepared),
            test_case_data.get("expected_prepared_count"),
            "failed expected_prepared check in {comment}".format(
                comment=test_case_data.get("comment")
            ),
        )
        self.assertEqual(
            len(not_published_articles),
            test_case_data.get("expected_not_published_count"),
            "failed expected_not_published check in {comment}".format(
                comment=test_case_data.get("comment")
            ),
        )
        if test_case_data.get("admin_email_content_contains"):
            for expected in test_case_data.get("admin_email_content_contains"):
                self.assertTrue(
                    expected in self.activity.admin_email_content,
                    "{expected} not found in admin_email_content for {comment}".format(
                        expected=expected, comment=test_case_data.get("comment")
                    ),
                )


@ddt
class TestChooseEmailType(unittest.TestCase):
    @data(
        {
            "comment": "insight article example",
            "article_type": "article-commentary",
            "is_poa": None,
            "was_ever_poa": None,
            "feature_article": False,
            "expected_email_type": "author_publication_email_Insight_to_VOR",
        },
        {
            "comment": "feature article example",
            "article_type": "discussion",
            "is_poa": None,
            "was_ever_poa": None,
            "feature_article": True,
            "expected_email_type": "author_publication_email_Feature",
        },
        {
            "comment": "POA article example",
            "article_type": "research-article",
            "is_poa": True,
            "was_ever_poa": None,
            "feature_article": False,
            "expected_email_type": "author_publication_email_POA",
        },
        {
            "comment": "VOR article with no previous POA example",
            "article_type": "research-article",
            "is_poa": False,
            "was_ever_poa": None,
            "feature_article": False,
            "expected_email_type": "author_publication_email_VOR_no_POA",
        },
        {
            "comment": "VOR article with no POA and False was_ever_poa example",
            "article_type": "research-article",
            "is_poa": False,
            "was_ever_poa": False,
            "feature_article": False,
            "expected_email_type": "author_publication_email_VOR_no_POA",
        },
        {
            "comment": "VOR article which had a POA example",
            "article_type": "research-article",
            "is_poa": False,
            "was_ever_poa": True,
            "feature_article": False,
            "expected_email_type": "author_publication_email_VOR_after_POA",
        },
        {
            "comment": "VOR review-article which was never a POA",
            "article_type": "review-article",
            "is_poa": False,
            "was_ever_poa": False,
            "feature_article": False,
            "expected_email_type": "author_publication_email_VOR_no_POA",
        },
        {
            "comment": "First RP reviewed preprint version example",
            "article_type": "preprint",
            "is_poa": None,
            "was_ever_poa": None,
            "feature_article": False,
            "version_doi": "10.7554/eLife.84364.1",
            "expected_email_type": "author_publication_email_RP_first_version",
        },
        {
            "comment": "Revised RP reviewed preprint version example",
            "article_type": "preprint",
            "is_poa": None,
            "was_ever_poa": None,
            "feature_article": False,
            "version_doi": "10.7554/eLife.84364.2",
            "expected_email_type": "author_publication_email_RP_revised_version",
        },
    )
    def test_choose_email_type(self, test_case_data):
        email_type = activity_module.choose_email_type(
            test_case_data.get("article_type"),
            test_case_data.get("is_poa"),
            test_case_data.get("was_ever_poa"),
            test_case_data.get("feature_article"),
            test_case_data.get("version_doi"),
        )
        self.assertEqual(
            email_type,
            test_case_data.get("expected_email_type"),
            "{expected} not found in admin_email_content for {comment}".format(
                expected=test_case_data.get("expected_email_type"),
                comment=test_case_data.get("comment"),
            ),
        )


class TestArticleAuthorsByArticleType(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(EJP, "get_authors")
    def test_article_authors_by_article_type(self, fake_ejp_get_authors):
        "test an insight article"
        fake_ejp_get_authors.return_value = EJP_ARTICLE_13_AUTHORS
        expected_author_count = 1

        article = articlelib.article()
        article.doi_id = 7
        article.article_type = "article-commentary"
        article.related_insight_article = articlelib.article()
        article.related_insight_article.doi_id = 13
        article.related_insight_article.authors = []
        # invoke
        authors = self.activity.article_authors_by_article_type(article)
        # assert
        self.assertEqual(len(authors), expected_author_count)


class TestGetEmailHeaders(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_template_get_email_headers_00013(self):
        self.activity.download_templates()

        email_type = "author_publication_email_VOR_no_POA"

        authors = fake_authors(self.activity, 13)

        article_object = articlelib.article()
        article_object.parse_article_file("tests/test_data/elife00013.xml")
        article_type = article_object.article_type
        feature_article = False
        related_insight_article = None
        features_email = "features_team@example.org"

        recipient_authors = activity_module.choose_recipient_authors(
            authors,
            article_type,
            feature_article,
            related_insight_article,
            features_email,
        )
        author = recipient_authors[2]

        email_format = "html"

        expected_headers = {
            "format": "html",
            "email_type": "author_publication_email_VOR_no_POA",
            "sender_email": "press@example.org",
            "subject": "Authoré, Your eLife paper is now online",
        }

        body = self.activity.templates.get_email_headers(
            email_type=email_type,
            author=author,
            article=article_object,
            format=email_format,
        )

        self.assertEqual(body, expected_headers)

    def test_template_get_email_headers_preprint(self):
        self.activity.download_templates()
        article_id = 91826
        email_type = "author_publication_email_RP_revised_version"

        authors = fake_preprint_authors(self.activity, article_id)
        article_object = articlelib.article()
        article_object.parse_article_file(
            "tests/files_source/publication_email/outbox/elife-preprint-91826-v2.xml"
        )
        article_type = article_object.article_type
        feature_article = False
        related_insight_article = None
        features_email = "features_team@example.org"
        recipient_authors = activity_module.choose_recipient_authors(
            authors,
            article_type,
            feature_article,
            related_insight_article,
            features_email,
        )
        author = recipient_authors[0]

        email_format = "html"

        expected_headers = {
            "format": "html",
            "email_type": "author_publication_email_RP_revised_version",
            "sender_email": "press@example.org",
            "subject": (
                "Your revised Reviewed Preprint has been published: "
                "10.7554/eLife.91826 Ex vivo Expansion Potential of "
                "Murine Hematopoietic Stem Cells: A Rare Property Only "
                "Partially Predicted by Phenotype"
            ),
        }

        body = self.activity.templates.get_email_headers(
            email_type=email_type,
            author=author,
            article=article_object,
            format=email_format,
        )

        self.assertEqual(body, expected_headers)


class TestGetEmailBody(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_template_get_email_body_00353(self):
        self.activity.download_templates()

        email_type = "author_publication_email_Feature"

        authors = fake_authors(self.activity)

        article_object = articlelib.article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = (
            "https://localhost.org/download-your-cover/00353"
        )
        article_type = article_object.article_type
        feature_article = True
        related_insight_article = None
        features_email = "features_team@example.org"

        recipient_authors = activity_module.choose_recipient_authors(
            authors,
            article_type,
            feature_article,
            related_insight_article,
            features_email,
        )
        author = recipient_authors[0]

        email_format = "html"

        expected_body = (
            'Header\n<p>Dear Features</p>\n"A good life"\n'
            + '<a href="https://doi.org/10.7554/eLife.00353">read it</a>\n'
            + '<a href="http://twitter.com/intent/tweet?text=https%3A%2F%2Fdoi.org%2F10.7554%2F'
            + 'eLife.00353+%40eLife">social media</a>\n'
            + '<a href="https://lens.elifesciences.org/00353">online viewer</a>\n'
            + '<a href="https://localhost.org/download-your-cover/00353">pdf cover</a>\n\n'
            + "author01@example.com\n\nauthor02@example.org\n\nauthor03@example.com\n"
        )

        body = self.activity.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article_object,
            authors=authors,
            format=email_format,
        )

        self.assertEqual(body, expected_body)


class TestGetPdfCoverPage(unittest.TestCase):
    def test_get_pdf_cover_page(self):
        article_object = articlelib.article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")
        article_object.pdf_cover_link = pdf_cover_page.get_pdf_cover_page(
            article_object.doi_id, settings_mock, FakeLogger()
        )
        self.assertEqual(
            article_object.pdf_cover_link,
            "https://localhost.org/download-your-cover/00353",
        )


class TestSendEmail(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        activity_module.SLEEP_SECONDS = 0.001
        activity_module.MAX_EMAILS_PER_SECOND = 1000
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch.object(activity_PublicationEmail, "send_author_email")
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
            with self.assertRaises(EmailRecipientException):
                self.activity.send_email(None, None, failed_author, None, None)

    @patch("provider.templates.Templates.get_email_body")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.email_provider, "smtp_send_message")
    def test_send_author_email(
        self, fake_send_message, fake_email_smtp_connect, fake_get_email_body
    ):
        # self.activity.download_templates()
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_get_email_body.return_value = "Body."
        fake_send_message.return_value = True
        author = {"e_mail": "author@example.org"}
        headers = {
            "email_type": "author_publication_email_VOR_no_POA",
            "format": "text",
            "sender_email": "sender@example.org",
            "subject": "Test",
        }
        doi_id = 99999

        result = self.activity.send_author_email(
            headers.get("email_type"), author, headers, None, None, doi_id
        )
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            ("Email sending details: result True, tries 1, article %s, email %s, to %s")
            % (doi_id, headers.get("email_type"), author.get("e_mail")),
        )

    @patch("provider.templates.Templates.get_email_body")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.email_provider, "smtp_send_message")
    def test_send_author_email_exception(
        self, fake_send_message, fake_email_smtp_connect, fake_get_email_body
    ):
        # self.activity.download_templates()
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_get_email_body.return_value = "Body."
        smtp_exception = smtplib.SMTPDataError(
            454, "Throttling failure: Maximum sending rate exceeded."
        )
        fake_send_message.side_effect = smtp_exception
        author = {"e_mail": "author@example.org"}
        headers = {
            "email_type": "author_publication_email_VOR_no_POA",
            "format": "text",
            "sender_email": "sender@example.org",
            "subject": "Test",
        }
        doi_id = 99999

        result = self.activity.send_author_email(
            headers.get("email_type"), author, headers, None, None, doi_id
        )
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                (
                    "Sending by SMTP reached smtplib.SMTPDataError, will sleep "
                    "%s seconds and then try again: %s"
                )
                % (activity_module.SLEEP_SECONDS, str(smtp_exception))
            ),
        )
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            ("Email sending details: result None, tries 3, article %s, email %s, to %s")
            % (doi_id, headers.get("email_type"), author.get("e_mail")),
        )


class TestApproveArticles(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch("provider.lax_provider.article_versions")
    def test_removes_articles_based_on_article_type(self, fake_article_versions):
        "test removing articles based on article type"
        fake_article_versions.return_value = (
            200,
            test_data.lax_article_versions_response_data,
        )
        research_article_doi = "10.7554/eLife.99996"
        editorial_article = helpers.instantiate_article(
            "editorial", "10.7554/eLife.99999"
        )
        correction_article = helpers.instantiate_article(
            "correction", "10.7554/eLife.99998"
        )
        retraction_article = helpers.instantiate_article(
            "retraction", "10.7554/eLife.99997"
        )
        research_article = helpers.instantiate_article(
            "research-article", research_article_doi, False, True
        )
        articles = [
            editorial_article,
            correction_article,
            retraction_article,
            research_article,
        ]
        approved_articles, not_published_articles = self.activity.approve_articles(
            articles
        )
        # one article will remain, the research-article
        self.assertEqual(len(approved_articles), 1)
        self.assertEqual(approved_articles[0].doi, research_article_doi)


class TestArticleAuthors(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )
        self.article_xml_authors = [
            {
                "surname": "Author",
                "given-names": "Article",
                "email": ["article_xml_author@example.org"],
                "corresp": True,
            }
        ]
        self.article_csv_authors = [
            {
                "surname": "Author",
                "given-names": "CSV",
                "email": ["article_csv_author@example.org"],
            }
        ]

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_PublicationEmail, "get_authors")
    def test_article_authors(self, fake_get_authors):
        "test getting authors for a research article"
        fake_get_authors.return_value = self.article_csv_authors
        doi_id = 3
        display_channel = "Research Article"
        expected = [
            {
                "surname": "Author",
                "given-names": "CSV",
                "email": ["article_csv_author@example.org"],
            },
            OrderedDict(
                [
                    ("e_mail", "article_xml_author@example.org"),
                    ("first_nm", "Article"),
                    ("last_nm", "Author"),
                ]
            ),
        ]

        article_object = articlelib.article()
        article_object.authors = self.article_xml_authors
        article_object.display_channel = display_channel

        all_authors = self.activity.article_authors(doi_id, article_object)
        self.assertEqual(all_authors, expected)

    @patch.object(activity_PublicationEmail, "get_authors")
    def test_article_authors_feature_article(self, fake_get_authors):
        "test getting authors for a feature article"
        fake_get_authors.return_value = self.article_csv_authors
        doi_id = 3
        display_channel = "Feature Article"
        expected = [
            {
                "surname": "Author",
                "given-names": "CSV",
                "email": ["article_csv_author@example.org"],
            },
        ]

        article_object = articlelib.article()
        article_object.authors = self.article_xml_authors
        article_object.display_channel = display_channel

        all_authors = self.activity.article_authors(doi_id, article_object)
        self.assertEqual(all_authors, expected)

    @patch.object(EJP, "get_preprint_authors")
    def test_article_authors_preprint(self, fake_get_preprint_authors):
        "test getting authors for a preprint article"
        fake_get_preprint_authors.return_value = EJP_ARTICLE_91826_AUTHORS
        doi_id = 91826
        version_doi = "10.7554/eLife.91826.2"
        article_type = "preprint"
        expected = [
            {
                "ms_no": "91826",
                "ms_rev_no": "1",
                "appeal_ind": "",
                "author_seq": "1",
                "first_nm": "Author",
                "last_nm": "Uno",
                "author_type_cde": "Contributing Author",
                "dual_corr_author_ind": "",
                "e_mail": "author91826-01@example.com",
                "primary_org": "University ",
            },
        ]

        article_object = articlelib.article()
        article_object.authors = []
        article_object.article_type = article_type
        article_object.version_doi = version_doi

        all_authors = self.activity.article_authors(doi_id, article_object)
        self.assertEqual(all_authors, expected)


class TestGetAuthorList(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_get_author_list(self):
        "test getting authors for a research article"
        column_headings = [
            "ms_no",
            "author_seq",
            "first_nm",
            "last_nm",
            "author_type_cde",
            "dual_corr_author_ind",
            "e_mail",
        ]
        authors = [
            [
                "3",
                "1",
                "Author",
                "One",
                "Contributing Author",
                " ",
                "author01@example.com",
            ]
        ]
        doi_id = "3"
        expected = [
            {
                "ms_no": "3",
                "author_seq": "1",
                "first_nm": "Author",
                "last_nm": "One",
                "author_type_cde": "Contributing Author",
                "dual_corr_author_ind": " ",
                "e_mail": "author01@example.com",
            }
        ]
        author_list = self.activity.get_author_list(column_headings, authors, doi_id)
        self.assertEqual(author_list, expected)

    def test_get_author_list_exception(self):
        "test for when column heading data is missing"
        column_headings = []
        authors = [
            [
                "3",
                "1",
                "Author",
                "One",
                "Contributing Author",
                " ",
                "author01@example.com",
            ]
        ]
        doi_id = "3"
        expected = [{}]
        author_list = self.activity.get_author_list(column_headings, authors, doi_id)
        self.assertEqual(author_list, expected)


@ddt
class TestChooseRecipientAuthors(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @data(
        (
            None,
            None,
            None,
            "features_team@example.org",
            "Author",
            "author01@example.com",
        ),
        (
            None,
            True,
            None,
            "features_team@example.org",
            "Features",
            "features_team@example.org",
        ),
        (
            None,
            None,
            "not_none",
            "features_team@example.org",
            "Features",
            "features_team@example.org",
        ),
        (
            "article-commentary",
            False,
            None,
            "features_team@example.org",
            "Features",
            "features_team@example.org",
        ),
        (
            "article-commentary",
            False,
            None,
            ["features_team@example.org"],
            "Features",
            "features_team@example.org",
        ),
    )
    @unpack
    def test_choose_recipient_authors(
        self,
        article_type,
        feature_article,
        related_insight_article,
        features_email,
        expected_0_first_nm,
        expected_0_e_mail,
    ):
        authors = fake_authors(self.activity)
        recipient_authors = activity_module.choose_recipient_authors(
            authors,
            article_type,
            feature_article,
            related_insight_article,
            features_email,
        )
        if recipient_authors:
            self.assertEqual(recipient_authors[0]["first_nm"], expected_0_first_nm)
            self.assertEqual(recipient_authors[0]["e_mail"], expected_0_e_mail)


class TestMergeRecipients(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PublicationEmail(
            settings_mock, fake_logger, None, None, None
        )
        # some list data as would be normally be produced and used
        self.list_one = [
            {
                "author_type_cde": "Contributing Author",
                "e_mail": "author13-01@example.com",
                "first_nm": "Author",
                "ms_no": "13",
                "dual_corr_author_ind": " ",
                "author_seq": "1",
                "last_nm": "Uno",
            },
            {
                "author_type_cde": "Contributing Author",
                "e_mail": "author13-02@example.com",
                "first_nm": "Author",
                "ms_no": "13",
                "dual_corr_author_ind": " ",
                "author_seq": "2",
                "last_nm": "Dos",
            },
        ]
        self.list_two = [
            OrderedDict(
                [
                    ("e_mail", "article_xml_recipient@example.org"),
                    ("first_nm", "First"),
                    ("last_nm", "Last"),
                ]
            )
        ]
        self.list_two_duplicate = [
            OrderedDict(
                [
                    ("e_mail", "author13-01@example.com"),
                    ("first_nm", "First"),
                    ("last_nm", "Last"),
                ]
            )
        ]

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_merge_recipients_empty(self):
        list_one = None
        list_two = None
        expected_count = 0
        merged_list = self.activity.merge_recipients(list_one, list_two)
        self.assertEqual(len(merged_list), expected_count)

    def test_merge_recipients_one_only(self):
        list_one = self.list_one
        list_two = None
        expected_count = 2
        merged_list = self.activity.merge_recipients(list_one, list_two)
        self.assertEqual(len(merged_list), expected_count)

    def test_merge_recipients_two_only(self):
        list_one = None
        list_two = self.list_two
        expected_count = 1
        merged_list = self.activity.merge_recipients(list_one, list_two)
        self.assertEqual(len(merged_list), expected_count)

    def test_merge_recipients(self):
        list_one = self.list_one
        list_two = self.list_two
        expected_count = 3
        merged_list = self.activity.merge_recipients(list_one, list_two)
        self.assertEqual(len(merged_list), expected_count)

    def test_merge_recipients_duplicate(self):
        list_one = self.list_one
        list_two = self.list_two_duplicate
        expected_count = 2
        merged_list = self.activity.merge_recipients(list_one, list_two)
        self.assertEqual(len(merged_list), expected_count)


class TestSendAdminEmail(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()

        class FakeSettings:
            def __init__(self):
                for attr in [
                    "domain",
                    "downstream_recipients_yaml",
                    "poa_packaging_bucket",
                    "ses_poa_sender_email",
                ]:
                    setattr(self, attr, getattr(settings_mock, attr, None))

        settings_object = FakeSettings()
        # email recipients is a list
        settings_object.ses_admin_email = ["one@example.org", "two@example.org"]

        self.activity = activity_PublicationEmail(
            settings_object, fake_logger, None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_send_admin_email(self, fake_email_smtp_connect):
        "test for when the email recipients is a list"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        activity_status = True
        result = self.activity.send_admin_email(activity_status)
        self.assertEqual(result, True)


class TestGetRelatedArticle(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_related_article_from_cache(self):
        "get related article from existing list of related articles"
        doi = "10.7554/eLife.15747"
        expected_doi = doi
        related_article = articlelib.article()
        related_article.parse_article_file("tests/test_data/elife-15747-v2.xml")
        return_value = activity_module.get_related_article(
            settings_mock, TempDirectory(), doi, [related_article], FakeLogger(), ""
        )
        self.assertEqual(return_value.doi, expected_doi)

    @patch("provider.article.create_article")
    def test_get_related_article_create_article(self, fake_create_article):
        "get related article from creating a new article for the doi"
        doi = "10.7554/eLife.15747"
        expected_doi = doi
        article_object = articlelib.article()
        article_object.parse_article_file("tests/test_data/elife-15747-v2.xml")
        fake_create_article.return_value = article_object
        related_articles = []
        return_value = activity_module.get_related_article(
            settings_mock, TempDirectory(), doi, related_articles, FakeLogger(), ""
        )
        self.assertEqual(return_value.doi, expected_doi)
        self.assertEqual(len(related_articles), 1)

    @patch("provider.article.create_article")
    def test_get_related_article_create_article_blank(self, fake_create_article):
        "test when creating a related article returns None"
        doi = "10.7554/eLife.15747"
        fake_create_article.return_value = None
        related_articles = []
        return_value = activity_module.get_related_article(
            settings_mock, TempDirectory(), doi, related_articles, FakeLogger(), ""
        )
        self.assertEqual(return_value, None)


class FakeArticle:
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
            "expected": [],
        },
        {
            "comment": "edge case None value",
            "prepared": [],
            "xml_file_to_doi_map": None,
            "do_not_remove": [],
            "do_remove": [],
            "expected": [],
        },
        {
            "comment": "normal clean one article",
            "prepared": [FakeArticle("1")],
            "xml_file_to_doi_map": OrderedDict([("1", "1.xml")]),
            "do_not_remove": [],
            "do_remove": [],
            "expected": ["outbox/1.xml"],
        },
        {
            "comment": "one article and do not clean it, by doi value",
            "prepared": [FakeArticle("1")],
            "xml_file_to_doi_map": OrderedDict([("1", "1.xml")]),
            "do_not_remove": ["1"],
            "do_remove": [],
            "expected": [],
        },
        {
            "comment": "one article prepared, one insight, clean both",
            "prepared": [FakeArticle("1")],
            "xml_file_to_doi_map": OrderedDict([("1", "1.xml"), ("2", "2.xml")]),
            "do_not_remove": [],
            "do_remove": [FakeArticle("2")],
            "expected": ["outbox/1.xml", "outbox/2.xml"],
        },
    )
    def test_s3_key_names_to_clean(self, test_case_data):
        "get related article from existing list of related articles"
        s3_key_names = activity_module.s3_key_names_to_clean(
            "outbox/",
            test_case_data.get("prepared"),
            test_case_data.get("xml_file_to_doi_map"),
            test_case_data.get("do_not_remove"),
            test_case_data.get("do_remove"),
        )
        self.assertEqual(
            s3_key_names,
            test_case_data.get("expected"),
            "failed check in {comment}".format(comment=test_case_data.get("comment")),
        )


@ddt
class TestAuthorsFromXML(unittest.TestCase):
    @data(
        {
            "comment": "older style xml with email in author notes, not supported",
            "filename": "elife00013.xml",
            "expected": [],
        },
        {
            "comment": "example of email in author aff",
            "filename": "elife-18753-v1.xml",
            "expected": [
                OrderedDict(
                    [
                        ("e_mail", "seppe@illinois.edu"),
                        ("first_nm", "Seppe"),
                        ("last_nm", "Kuehn"),
                    ]
                ),
            ],
        },
        {
            "comment": "newer style XML example",
            "filename": "elife-32991-v2.xml",
            "expected": [
                OrderedDict(
                    [
                        ("e_mail", "alhonore@hotmail.com"),
                        ("first_nm", "Aurore"),
                        ("last_nm", "L'honoré"),
                    ]
                ),
                OrderedDict(
                    [
                        ("e_mail", "didier.montarras@pasteur.fr"),
                        ("first_nm", "Didier"),
                        ("last_nm", "Montarras"),
                    ]
                ),
            ],
        },
    )
    def test_authors_from_xml(self, test_case_data):
        article_object = articlelib.article()
        full_filename = os.path.join(
            "tests",
            "files_source",
            "publication_email",
            "outbox",
            test_case_data.get("filename"),
        )
        article_object.parse_article_file(full_filename)
        authors = activity_module.authors_from_xml(article_object)
        self.assertEqual(authors, test_case_data.get("expected"))
