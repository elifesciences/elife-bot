import unittest
import os
import shutil
import provider.templates as templates_provider
from provider.templates import Templates
from provider.article import article
import tests.settings_mock as settings_mock
from testfixtures import tempdir
from testfixtures import TempDirectory
from mock import patch, MagicMock
from ddt import ddt, data, unpack


@ddt
class TestProviderTemplates(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.templates = Templates(settings_mock, tmp_dir=self.directory.path)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def copy_email_templates(self):
        templates_path = "tests/test_data/templates"
        for template_file in os.listdir(templates_path):
            source_doc = os.path.join(templates_path, template_file)
            dest_doc = os.path.join(self.directory.path, template_file)
            shutil.copy(source_doc, dest_doc)

    def test_copy_lens_templates(self):
        from_dir = os.path.join("tests", "test_data", "templates")
        self.templates.copy_lens_templates(from_dir)
        self.assertTrue(self.templates.lens_templates_warmed)

    def test_get_email_body(self):
        # set templates to warmed and copy some template files
        email_type = "author_publication_email"
        email_format = "html"
        author = {"first_nm": "Test"}
        article_data = {"doi_url": "http://doi.org/"}
        authors = None
        expected_body = 'Header\n<p>Dear Test, <a href="http://doi.org/">read it</a> online.</p>\nFooter'
        # copy the email template files
        self.copy_email_templates()
        self.templates.email_templates_warmed = True
        # render the email body
        body = self.templates.get_email_body(
            email_type, author, article_data, authors, email_format
        )
        self.assertEqual(body, expected_body)

    def test_get_email_body_exception(self):
        # test for when templates are not warmed
        self.templates.email_templates_warmed = False
        with self.assertRaises(Exception):
            self.templates.get_email_body(None, None, None, None)

    @data(
        (
            "author_publication_email",
            "html",
            {},
            "press@elifesciences.org",
            "author_publication_email",
            "Test, Your eLife paper is now online",
            "html",
        ),
    )
    @unpack
    def test_get_email_headers(
        self,
        email_type,
        email_format,
        expected_headers_type,
        expected_sender_email,
        expected_email_type,
        expected_subject,
        expected_format,
    ):

        # set templates to warmed and copy some template files
        self.copy_email_templates()
        self.templates.email_templates_warmed = True
        author = {"first_nm": "Test"}
        article_data = {"doi_url": "http://doi.org/"}
        headers = self.templates.get_email_headers(
            email_type, author, article_data, email_format
        )
        self.assertEqual(type(headers), type(expected_headers_type))
        if headers:
            # compare more values if headers were produced
            self.assertEqual(headers.get("sender_email"), expected_sender_email)
            self.assertEqual(headers.get("email_type"), expected_email_type)
            self.assertEqual(headers.get("subject"), expected_subject)
            self.assertEqual(headers.get("format"), expected_format)

    def test_get_email_headers_exception(self):
        # test rendering headers for when templates are not warmed
        self.templates.email_templates_warmed = False
        with self.assertRaises(Exception):
            self.templates.get_email_headers(None, None, None)

    def test_get_email_headers_vor_after_poa(self):
        """test for backslash and quotation mark in article title"""
        # set templates to warmed and copy some template files
        self.copy_email_templates()
        self.templates.email_templates_warmed = True
        author = {"first_nm": "Test"}
        article_data = {
            "doi": "10.7554/eLife.00666",
            "article_title": 'Test \\ and " in article',
        }
        email_type = "author_publication_email_VOR_after_POA"
        email_format = "html"

        expected_headers_type = {}
        expected_sender_email = "press@example.org"
        expected_email_type = email_type
        expected_subject = (
            "The full version of your eLife article is now available:"
            ' 10.7554/eLife.00666 Test \\ and " in article'
        )
        expected_format = email_format

        headers = self.templates.get_email_headers(
            email_type, author, article_data, email_format
        )
        self.assertEqual(type(headers), type(expected_headers_type))
        if headers:
            # compare more values if headers were produced
            self.assertEqual(headers.get("sender_email"), expected_sender_email)
            self.assertEqual(headers.get("email_type"), expected_email_type)
            self.assertEqual(headers.get("subject"), expected_subject)
            self.assertEqual(headers.get("format"), expected_format)

    @data(
        (
            "tests/test_data/templates/",
            '<!DOCTYPE html>\n<html xmlns:mml="http://www.w3.org/1998/Math/MathML">\n<head>\n<title>Differential TAM receptor\u2013ligand\u2013phospholipid interactions delimit differential TAM bioactivities | eLife Lens</title>\n<script>\ndocument_url: "http://example.com/cdn-bucket/elife03385.xml"\n</script>\n</head>\n<body>\n</body>\n</html>',
        ),
        ("", None),
    )
    @unpack
    def test_lens_article_html(self, from_dir, expected_content):
        article_xml_filename = "elife03385.xml"
        article_xml_path = "tests/test_data/" + article_xml_filename
        article_object = article(settings_mock, tmp_dir=self.directory.path)
        article_object.parse_article_file(article_xml_path)
        cdn_bucket = "cdn-bucket"
        content = self.templates.get_lens_article_html(
            from_dir, article_object, cdn_bucket, article_xml_filename
        )
        self.assertEqual(content, expected_content)


@ddt
class TestProviderTemplatesFunctions(unittest.TestCase):
    @data(
        {"string": "Test", "expected": "Test"},
        {
            "string": 'Test \\ and " in article',
            "expected": 'Test \\\\ and \\" in article',
        },
    )
    def test_json_char_escape(self, test_data):
        new_string = templates_provider.json_char_escape(test_data.get("string"))
        self.assertEqual(new_string, test_data.get("expected"))

    @data(
        {"article_title": "Test", "expected": "Test"},
        {
            "article_title": 'Test \\ and " in article',
            "expected": 'Test \\\\ and \\" in article',
        },
    )
    def test_article_title_char_escape(self, test_data):
        test_article = article()
        test_article.article_title = test_data.get("article_title")
        test_article = templates_provider.article_title_char_escape(test_article)
        self.assertEqual(test_article.article_title, test_data.get("expected"))


if __name__ == "__main__":
    unittest.main()
