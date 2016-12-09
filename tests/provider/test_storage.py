import unittest
from mock import MagicMock, call
from provider.storage_provider import S3StorageContext

class TestProviderStorage(unittest.TestCase):
    def setUp(self):
        self.storage = S3StorageContext({})
        self.storage.context['buckets']['a'] = MagicMock()
        self.storage.context['buckets']['b'] = MagicMock()
        self.storage.context['connection'] = MagicMock()

    def test_copy_without_any_metadata_to_override(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(original, destination, None)
        self.assertEqual({'metadata': None}, self.storage.context['buckets']['b'].copy_key.mock_calls[0][2])

    def test_copy_and_specify_metadata(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(original, destination, {'Content-Type': 'application/json'})
        self.assertEqual({'metadata': {'Content-Type': 'application/json'}}, self.storage.context['buckets']['b'].copy_key.mock_calls[0][2])

        
