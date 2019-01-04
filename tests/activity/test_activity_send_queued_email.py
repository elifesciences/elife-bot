import unittest
from mock import patch
from provider.simpleDB import SimpleDB
import activity.activity_SendQueuedEmail as activity_module
from activity.activity_SendQueuedEmail import activity_SendQueuedEmail as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeS3Connection, FakeBucket, FakeKey
from testfixtures import TempDirectory


class FakeItem(object):
    "mock boto.sdb.item.Item object"

    def __init__(self, domain='', name=''):
        self.domain = domain
        self.name = name
        self._dict = dict()

    def __getitem__(self, key):
        return self._dict.get(key)

    def __setitem__(self, key, value):
        self._dict[key] = value


def email_items():
    "test data as mocked boto.sdb.item.Item objects"
    email_items = []
    good_email_item = FakeItem('domain', 'good_item_name')
    good_email_item['sender_name'] = 'example'
    good_email_item['sender_email'] = 'elife@example.org'
    good_email_item['recipient_email'] = 'elife@example.org'
    good_email_item['subject'] = 'Test case'
    good_email_item['format'] = 'text'
    good_email_item['body_s3key'] = 'key'
    email_items.append(good_email_item)
    incomplete_email_item = FakeItem('domain', 'item_name')
    email_items.append(incomplete_email_item)
    return email_items


class TestSendQueuedEmail(unittest.TestCase):

    def setUp(self):
        self.activity = activity_object(settings_mock, FakeLogger(), None, None, None)
        # send one per second to test sleep
        self.activity.rate_limit_per_sec = 1

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('boto.ses.connect_to_region')
    @patch.object(FakeKey, 'get_contents_as_string')
    @patch.object(FakeBucket, 'get_key')
    @patch.object(FakeS3Connection, 'lookup')
    @patch.object(activity_module, 'S3Connection')
    @patch.object(SimpleDB, 'put_attributes')
    @patch.object(SimpleDB, 'elife_get_email_queue_items')
    def test_do_activity(self, fake_get_email, fake_put, fake_s3_mock,
                         fake_lookup, fake_key, fake_contents, fake_ses_connection):
        fake_s3_mock.return_value = FakeS3Connection()
        fake_lookup.return_value = FakeBucket()
        fake_key.return_value = FakeKey(TempDirectory())
        fake_contents.return_value = 'body'
        fake_get_email.return_value = email_items()
        result = self.activity.do_activity()
        self.assertTrue(result)
