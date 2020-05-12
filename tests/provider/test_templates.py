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
        for template_file in self.templates.get_email_templates_list():
            source_doc = 'tests/test_data/templates/' + template_file
            dest_doc = os.path.join(self.directory.path, template_file)
            shutil.copy(source_doc, dest_doc)

    def test_get_email_templates_list(self):
        self.assertTrue(len(self.templates.get_email_templates_list()) > 0)


    def test_get_lens_templates_list(self):
        self.assertTrue(len(self.templates.get_lens_templates_list()) > 0)


    def test_copy_lens_templates(self):
        from_dir = os.path.join('tests', 'test_data', 'templates')
        self.templates.copy_lens_templates(from_dir)
        self.assertTrue(self.templates.lens_templates_warmed)


    def test_save_template_contents_to_tmp_dir(self):
        contents = "contents"
        template_name = "template_name"
        result = self.templates.save_template_contents_to_tmp_dir(contents, template_name)
        self.assertTrue(result)


    @data(
        ('email', 'email_header.html', 'email_templates/email_header.html'),
        ('foo', 'email_header.html', None)
        )
    @unpack
    def test_get_s3_key_name(self, template_type, template_name, expected_s3_key_name):
        s3_key_name = self.templates.get_s3_key_name(template_type, template_name)
        self.assertEqual(s3_key_name, expected_s3_key_name)


    @patch('provider.templates.Templates.download_email_templates_from_s3')
    @data(
        ('author_publication_email', True, 'html',
         'Header\n<p>Dear Test, <a href="http://doi.org/">read it</a> online.</p>\nFooter'),
        ('author_publication_email', False, 'html',
         None),
        )
    @unpack
    def test_get_email_body(self, email_type, warm_templates, format, expected_body,
                            fake_download_email_templates_from_s3):
        fake_download_email_templates_from_s3 = MagicMock()
        # set templates to warmed and copy some template files
        if warm_templates is True:
            self.copy_email_templates()
            self.templates.email_templates_warmed = True
        author = {"first_nm": "Test"}
        article_data = {"doi_url": "http://doi.org/"}
        authors = None
        body = self.templates.get_email_body(email_type, author, article_data, authors, format)
        self.assertEqual(body, expected_body)


    @patch('provider.templates.Templates.download_email_templates_from_s3')
    @data(
        ('author_publication_email', True, 'html',
         {}, 'press@elifesciences.org', 'author_publication_email',
         'Test, Your eLife paper is now online', 'html'),
        ('author_publication_email', False, 'html',
         None, '', '', '', ''),
        )
    @unpack
    def test_get_email_headers(self, email_type, warm_templates, format,
                               expected_headers_type, expected_sender_email, expected_email_type,
                               expected_subject, expected_format,
                               fake_download_email_templates_from_s3):
        fake_download_email_templates_from_s3 = MagicMock()
        # set templates to warmed and copy some template files
        if warm_templates is True:
            self.copy_email_templates()
            self.templates.email_templates_warmed = True
        author = {"first_nm": "Test"}
        article_data = {"doi_url": "http://doi.org/"}
        headers = self.templates.get_email_headers(email_type, author, article_data, format)
        self.assertEqual(type(headers), type(expected_headers_type))
        if headers:
            # compare more values if headers were produced
            self.assertEqual(headers.get('sender_email'), expected_sender_email)
            self.assertEqual(headers.get('email_type'), expected_email_type)
            self.assertEqual(headers.get('subject'), expected_subject)
            self.assertEqual(headers.get('format'), expected_format)

    @patch('provider.templates.Templates.download_email_templates_from_s3')
    def test_get_email_headers_vor_after_poa(self, fake_download_email_templates_from_s3):
        """test for backslash and quotation mark in article title"""
        fake_download_email_templates_from_s3 = MagicMock()
        # set templates to warmed and copy some template files
        self.copy_email_templates()
        self.templates.email_templates_warmed = True
        author = {"first_nm": "Test"}
        article_data = {
            "doi": "10.7554/eLife.00666",
            "article_title": 'Test \\ and \" in article'
            }
        email_type = 'author_publication_email_VOR_after_POA'
        email_format = 'html'

        expected_headers_type = {}
        expected_sender_email = 'press@example.org'
        expected_email_type = email_type
        expected_subject = (
            'The full version of your eLife article is now available:'
            ' 10.7554/eLife.00666 Test \\ and \" in article')
        expected_format = email_format

        headers = self.templates.get_email_headers(email_type, author, article_data, email_format)
        self.assertEqual(type(headers), type(expected_headers_type))
        if headers:
            # compare more values if headers were produced
            self.assertEqual(headers.get('sender_email'), expected_sender_email)
            self.assertEqual(headers.get('email_type'), expected_email_type)
            self.assertEqual(headers.get('subject'), expected_subject)
            self.assertEqual(headers.get('format'), expected_format)

    @data(
        ('tests/test_data/templates/', u'<!DOCTYPE html>\n<html xmlns:mml="http://www.w3.org/1998/Math/MathML">\n<head>\n<title>Differential TAM receptor\u2013ligand\u2013phospholipid interactions delimit differential TAM bioactivities | eLife Lens</title>\n<script>\ndocument_url: "http://example.com/cdn-bucket/elife03385.xml"\n</script>\n</head>\n<body>\n</body>\n</html>'),
        ('', None)
        )
    @unpack
    def test_lens_article_html(self, from_dir, expected_content):
        article_xml_filename = 'elife03385.xml'
        article_xml_path = 'tests/test_data/' + article_xml_filename
        article_object = article(settings_mock, tmp_dir=self.directory.path)
        article_object.parse_article_file(article_xml_path)
        cdn_bucket = 'cdn-bucket'
        content = self.templates.get_lens_article_html(from_dir, article_object, cdn_bucket, article_xml_filename)
        self.assertEqual(content, expected_content)


@ddt
class TestProviderTemplatesFunctions(unittest.TestCase):

    @data(
        {
            'string': 'Test',
            'expected': 'Test'
        },
        {
            'string': 'Test \\ and \" in article',
            'expected': 'Test \\\\ and \\" in article'
        },
    )
    def test_json_char_escape(self, test_data):
        new_string = templates_provider.json_char_escape(test_data.get('string'))
        self.assertEqual(new_string, test_data.get('expected'))

    @data(
        {
            'article_title': 'Test',
            'expected': 'Test'
        },
        {
            'article_title': 'Test \\ and \" in article',
            'expected': 'Test \\\\ and \\" in article'
        },
    )
    def test_article_title_char_escape(self, test_data):
        test_article = article()
        test_article.article_title = test_data.get('article_title')
        test_article = templates_provider.article_title_char_escape(test_article)
        self.assertEqual(test_article.article_title, test_data.get('expected'))


if __name__ == '__main__':
    unittest.main()
