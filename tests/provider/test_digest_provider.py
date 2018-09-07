import unittest
import os
from digestparser.objects import Digest, Image
import provider.digest_provider as digest_provider


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
