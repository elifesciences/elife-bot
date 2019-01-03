import unittest
from mock import patch
from provider.simpleDB import SimpleDB
import activity.activity_S3Monitor as activity_module
from activity.activity_S3Monitor import activity_S3Monitor as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeS3Connection, FakeBucket
from boto.s3.prefix import Prefix
from boto.s3.key import Key


BUCKET_NAME = 'origin_bucket'


TEST_DATA = {
    'data': {
        'bucket': BUCKET_NAME
    }
}


def bucket_list_data():
    "some fake S3 Prefix and Key data to look at"
    bucket_list = []
    bucket_list.append(Prefix(BUCKET_NAME, '00003/'))
    fake_key = Key(FakeBucket(), '00003/file.zip')
    fake_key.last_modified = '2013-01-26T23:48:28.000Z'
    bucket_list.append(fake_key)
    return bucket_list


class TestS3Monitor(unittest.TestCase):

    def setUp(self):
        self.activity = activity_object(settings_mock, FakeLogger(), None, None, None)

    @patch.object(FakeBucket, 'list')
    @patch.object(FakeS3Connection, 'lookup')
    @patch.object(activity_module, 'S3Connection')
    @patch.object(SimpleDB, 'get_item')
    def test_do_activity(self, fake_get_item, fake_s3_mock, fake_lookup, fake_list):
        fake_s3_mock.return_value = FakeS3Connection()
        fake_lookup.return_value = FakeBucket()
        fake_list.return_value = bucket_list_data()
        result = self.activity.do_activity(TEST_DATA)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
