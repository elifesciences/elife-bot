import unittest
import os
import tests.settings_mock as settings_mock
from digestparser.objects import Digest, Image
from mock import patch, MagicMock
import provider.digest_provider as digest_provider
from provider.digest_provider import ErrorCallingDigestException


class TestDigestProvider(unittest.TestCase):

    def test_outbox_dest_resource_path(self):
        "test building the path to the bucket folder"
        storage_provider = 's3'
        digest = Digest()
        digest.doi = '10.7554/eLife.99999'
        bucket_name = 'elife-bot'
        expected = 's3://elife-bot/digests/outbox/99999/'
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
        expected_status_code = 200
        expected_data = {'id': u'99999'}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'id': u'99999'}
        mock_requests_get.return_value = response
        status_code, data = digest_provider.get_digest('99999', settings_mock)
        self.assertEqual(status_code, expected_status_code)
        self.assertEqual(data, expected_data)

    @patch('requests.get')
    def test_get_digest_404(self, mock_requests_get):
        expected_status_code = 404
        response = MagicMock()
        response.status_code = expected_status_code
        mock_requests_get.return_value = response
        status_code, data = digest_provider.get_digest('99999', settings_mock)
        self.assertEqual(status_code, expected_status_code)
        self.assertIsNone(data)

    @patch('requests.get')
    def test_get_digest_500(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 500
        mock_requests_get.return_value = response
        self.assertRaises(ErrorCallingDigestException, digest_provider.get_digest,
                          '99999', settings_mock)
