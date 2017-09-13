import unittest
import os
import shutil
from provider.templates import Templates
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
        article = {"doi_url": "http://doi.org/"}
        authors = None
        body = self.templates.get_email_body(email_type, author, article, authors, format)
        self.assertEqual(body, expected_body)


if __name__ == '__main__':
    unittest.main()
