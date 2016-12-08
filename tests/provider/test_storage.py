import unittest
from mock import MagicMock
from provider.storage_provider import S3StorageContext

class TestProviderStorage(unittest.TestCase):
    def test_copy_without_any_metadata_to_override(self):
        storage = S3StorageContext({})
        storage.context['buckets']['a'] = MagicMock()
        storage.context['buckets']['b'] = MagicMock()
        storage.context['connection'] = MagicMock()
        original = "s3://a/1"
        destination = "s3://b/2"
        storage.copy_resource(original, destination, None)
        self.assertIsNone(None, storage.context['buckets']['b'].method_calls[1][2]['metadata'])
        
