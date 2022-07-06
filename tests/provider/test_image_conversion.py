import unittest
import os
from mock import patch
from testfixtures import TempDirectory
from provider import article_structure, image_conversion
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


class TestImageConversion(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.formats = {
            "Original": {"sources": "tif", "format": "jpg", "download": "yes"}
        }
        self.image_file_base = "elife-00353-fig1-v1"
        self.tif_file = "%s.tif" % self.image_file_base
        self.file_pointer = open(
            os.path.join("tests", "files_source", self.tif_file), "rb"
        )

    def tearDown(self):
        self.file_pointer.close()
        TempDirectory.cleanup_all()

    @patch.object(image_conversion, "storage_context")
    def test_generate_images(self, fake_storage_context):
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path, dest_folder=directory.path
        )

        info = article_structure.ArticleInfo(self.tif_file)

        cdn_bucket_name = (
            settings_mock.publishing_buckets_prefix + settings_mock.ppp_cdn_bucket
        )
        cdn_resource_path = (
            settings_mock.storage_provider + "://" + cdn_bucket_name + "/"
        )
        publish_locations = [cdn_resource_path]

        image_conversion.generate_images(
            settings_mock,
            self.formats,
            self.file_pointer,
            info,
            publish_locations,
            self.logger,
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "Stored image %s.jpg as ['s3://%s/']"
            % (self.image_file_base, cdn_bucket_name),
        )

    @patch("provider.imageresize.resize")
    @patch.object(image_conversion, "storage_context")
    def test_generate_images_resize_error(self, fake_storage_context, fake_resize):
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path, dest_folder=directory.path
        )
        info = article_structure.ArticleInfo(self.tif_file)
        publish_locations = []
        fake_resize.return_value = None, None
        with self.assertRaises(RuntimeError):
            image_conversion.generate_images(
                settings_mock,
                self.formats,
                self.file_pointer,
                info,
                publish_locations,
                self.logger,
            )
