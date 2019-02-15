# coding=utf-8
 
import unittest
import os
import copy
import tests.settings_mock as settings_mock
from digestparser.objects import Digest, Image
from mock import patch, MagicMock
from tests.activity.helpers import create_digest
import tests.test_data as test_data
import provider.digest_provider as digest_provider
from provider.digest_provider import ErrorCallingDigestException
from tests import read_fixture
from tests.activity.classes_mock import FakeLogger


class TestDigestProvider(unittest.TestCase):

    def test_outbox_dest_resource_path(self):
        "test building the path to the bucket folder"
        storage_provider = 's3'
        digest = Digest()
        digest.doi = '10.7554/eLife.99999'
        bucket_name = 'elife-bot'
        expected = 's3://elife-bot/digests/outbox/99999'
        resource_path = digest_provider.outbox_dest_resource_path(
            storage_provider, digest, bucket_name)
        self.assertEqual(resource_path, expected)

    def test_outbox_file_dest_resource(self):
        "test the bucket destination resource path for a file"
        storage_provider = 's3'
        digest = Digest()
        digest.doi = '10.7554/eLife.99999'
        bucket_name = 'elife-bot'
        # create a full path to test stripping out folder names
        file_path = os.getcwd() + os.sep + 'DIGEST 99999.docx'
        expected = 's3://elife-bot/digests/outbox/99999/digest-99999.docx'
        dest_resource = digest_provider.outbox_file_dest_resource(
            storage_provider, digest, bucket_name, file_path)
        self.assertEqual(dest_resource, expected)

    def test_has_image(self):
        "test when a digest has an image"
        digest = Digest()
        image = Image()
        image.file = 'something'
        digest.image = image
        self.assertEqual(digest_provider.has_image(digest), True)

    def test_has_image_no_image(self):
        "test when a digest has no image"
        digest = Digest()
        self.assertEqual(digest_provider.has_image(digest), False)

    def test_has_image_no_file(self):
        "test when a digest has an image but no file"
        digest = Digest()
        digest.image = Image()
        self.assertEqual(digest_provider.has_image(digest), False)

    @patch('requests.get')
    def test_get_digest_200(self, mock_requests_get):
        expected_data = {'id': u'99999'}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'id': u'99999'}
        mock_requests_get.return_value = response
        data = digest_provider.get_digest('99999', settings_mock)
        self.assertEqual(data, expected_data)

    @patch('requests.get')
    def test_get_digest_404(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 404
        mock_requests_get.return_value = response
        data = digest_provider.get_digest('99999', settings_mock)
        self.assertIsNone(data)

    @patch('requests.get')
    def test_get_digest_500(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 500
        mock_requests_get.return_value = response
        self.assertRaises(ErrorCallingDigestException, digest_provider.get_digest,
                          '99999', settings_mock)

    @patch('requests.get')
    def test_get_digest_preview(self, mock_requests_get):
        expected_data = {'id': u'99999'}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'id': u'99999'}
        mock_requests_get.return_value = response
        data = digest_provider.get_digest_preview('99999', settings_mock)
        request_named_arguments = mock_requests_get.call_args_list[0][1]
        headers = request_named_arguments['headers']
        self.assertIn('Authorization', headers)
        self.assertEqual(data, expected_data)

    @patch('requests.put')
    def test_put_digest_204(self, mock_requests_put):
        digest_id = '99999'
        data = {}
        response = MagicMock()
        response.status_code = 204
        mock_requests_put.return_value = response
        # cannot depend on a return value, just check there is no exception
        try:
            digest_provider.put_digest(digest_id, data, settings_mock)
        except ErrorCallingDigestException:
            self.assertFalse(True)

    @patch('requests.put')
    def test_put_digest_request_headers(self, mock_requests_put):
        digest_id = '99999'
        data = {}
        response = MagicMock()
        response.status_code = 204
        mock_requests_put.return_value = response
        digest_provider.put_digest(digest_id, data, settings_mock)
        request_named_arguments = mock_requests_put.call_args_list[0][1]
        headers = request_named_arguments['headers']
        self.assertIn('Authorization', headers)
        self.assertIn('Content-Type', headers)
        self.assertEqual(headers['Content-Type'], 'application/vnd.elife.digest+json; version=1')

    @patch('requests.put')
    def test_put_digest_400(self, mock_requests_put):
        digest_id = '99999'
        data = {}
        response = MagicMock()
        response.status_code = 400
        mock_requests_put.return_value = response
        self.assertRaises(ErrorCallingDigestException, digest_provider.put_digest,
                          digest_id, data, settings_mock)

    @patch('requests.put')
    def test_put_digest_403(self, mock_requests_put):
        digest_id = '99999'
        data = {}
        response = MagicMock()
        response.status_code = 403
        mock_requests_put.return_value = response
        self.assertRaises(ErrorCallingDigestException, digest_provider.put_digest,
                          digest_id, data, settings_mock)

    @patch('provider.lax_provider.article_versions')
    def test_published_date_from_lax(self, fake_article_versions):
        fake_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        published = digest_provider.published_date_from_lax(settings_mock, '08411')
        self.assertEqual(published, "2015-12-29T00:00:00Z")

    @patch('provider.lax_provider.article_versions')
    def test_published_date_from_lax_no_vor(self, fake_article_versions):
        versions_data = copy.copy(test_data.lax_article_versions_response_data)
        # delete the vor data
        del(versions_data[2])
        print(versions_data)
        fake_article_versions.return_value = 200, versions_data
        published = digest_provider.published_date_from_lax(settings_mock, '08411')
        self.assertEqual(published, None)

    @patch('provider.lax_provider.article_versions')
    def test_published_date_from_lax_no_data(self, fake_article_versions):
        fake_article_versions.return_value = 200, []
        published = digest_provider.published_date_from_lax(settings_mock, '08411')
        self.assertEqual(published, None)


class TestBuildDigest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = os.path.join('tests/tmp')

    def test_digest_unicode(self):
        """test a digest zip with a unicode docx file name"""
        input_file = os.path.join('tests', 'files_source', 'DIGEST_35774.zip')
        expected_status = True
        expected_author = u'Bayés'
        build_status, digest = digest_provider.build_digest(
            input_file, self.temp_dir)
        self.assertEqual(build_status, expected_status)
        self.assertEqual(digest.author, expected_author)


class TestDigestJats(unittest.TestCase):

    def setUp(self):
        self.temp_dir = os.path.join('temp')
        self.logger = FakeLogger()
        self.digest_config = digest_provider.digest_config(
            settings_mock.digest_config_section,
            settings_mock.digest_config_file)

    def test_digest_jats(self):
        "convert digest docx file into JATS output, consisting of text paragraphs"
        input_file = os.path.join('tests', 'files_source', 'DIGEST 99999.docx')
        folder_name = "digests"
        expected_output = read_fixture('jats_content_99999.py', folder_name)
        build_status, digest = digest_provider.build_digest(
            input_file, self.temp_dir, self.logger, self.digest_config)
        jats_content = digest_provider.digest_jats(digest, self.logger)
        self.assertEqual(jats_content, expected_output)

    def test_digest_jats_none(self):
        "test building jats from a bad file input"
        input_file = None
        build_status, digest = digest_provider.build_digest(
            input_file, self.temp_dir, self.logger, self.digest_config)
        jats_content = digest_provider.digest_jats(digest, self.logger)
        self.assertEqual(jats_content, None)


class TestValidateDigest(unittest.TestCase):

    def test_validate_digest(self):
        "approving good Digest content"
        digest_content = create_digest('Anonymous', '10.7554/eLife.99999', ['text'])
        expected_status = True
        expected_error_messages = []
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)

    def test_validate_digest_no_digest(self):
        "approving missing Digest"
        digest_content = None
        expected_status = False
        expected_error_messages = ['Digest was empty']
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)

    def test_validate_digest_empty_digest(self):
        "approving an empty Digest"
        digest_content = Digest()
        expected_status = False
        expected_error_messages = ['Digest author is missing', 'Digest DOI is missing',
                                   'Digest text is missing']
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)

    def test_validate_digest_digest_no_author(self):
        "approving an empty Digest"
        digest_content = create_digest(None, '10.7554/eLife.99999', ['text'])
        expected_status = False
        expected_error_messages = ['Digest author is missing']
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)

    def test_validate_digest_digest_no_doi(self):
        "approving an empty Digest"
        digest_content = create_digest('Anonymous', None, ['text'])
        expected_status = False
        expected_error_messages = ['Digest DOI is missing']
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)

    def test_validate_digest_digest_no_text(self):
        "approving an empty Digest"
        digest_content = create_digest('Anonymous', '10.7554/eLife.99999', None)
        expected_status = False
        expected_error_messages = ['Digest text is missing']
        status, error_messages = digest_provider.validate_digest(digest_content)
        self.assertEqual(status, expected_status)
        self.assertEqual(error_messages, expected_error_messages)


class TestSilentDigest(unittest.TestCase):

    def test_silent_digest_not_silent_zip(self):
        self.assertFalse(digest_provider.silent_digest('DIGEST 99999.zip'))

    def test_silent_digest_not_silent_docx(self):
        self.assertFalse(digest_provider.silent_digest('DIGEST 99999.docx'))

    def test_silent_digest_is_silent_zip(self):
        self.assertTrue(digest_provider.silent_digest('DIGEST 99999 SILENT.zip'))

    def test_silent_digest_is_hyphen_silent_zip(self):
        self.assertTrue(digest_provider.silent_digest('DIGEST 99999-Silent.zip'))

    def test_silent_digest_is_silent_docx(self):
        self.assertTrue(digest_provider.silent_digest('DIGEST 99999 SILENT.docx'))

    def test_silent_digest_none(self):
        self.assertFalse(digest_provider.silent_digest(None))
