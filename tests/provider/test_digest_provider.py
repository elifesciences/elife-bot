import unittest
import os
import copy
import tests.settings_mock as settings_mock
from digestparser.objects import Digest, Image
from mock import patch, MagicMock
import provider.digest_provider as digest_provider
from provider.digest_provider import ErrorCallingDigestException
import tests.test_data as test_data


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
