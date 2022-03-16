import unittest
from mock import MagicMock
from provider.storage_provider import S3StorageContext
from tests import settings_mock


class TestProviderStorage(unittest.TestCase):
    def setUp(self):
        self.storage = S3StorageContext(settings_mock)
        self.storage.context["client"] = MagicMock()

    def test_copy_without_any_metadata_to_override(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(original, destination, None)
        self.storage.context["client"].copy_object.assert_called()
        self.assertEqual(
            {"Bucket": "b", "CopySource": {"Bucket": "a", "Key": "1"}, "Key": "2"},
            self.storage.context["client"].copy_object.mock_calls[0][2],
        )

    def test_copy_and_specify_metadata(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(
            original,
            destination,
            {
                "Content-Type": "application/json",
                "Content-Disposition": "Content-Disposition: attachment; filename=2;",
            },
        )
        self.assertEqual(
            {
                "CopySource": {"Bucket": "a", "Key": "1"},
                "Bucket": "b",
                "Key": "2",
                "MetadataDirective": "REPLACE",
                "ContentType": "application/json",
                "ContentDisposition": "Content-Disposition: attachment; filename=2;",
            },
            self.storage.context["client"].copy_object.mock_calls[0][2],
        )
