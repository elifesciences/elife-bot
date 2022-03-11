import unittest
from mock import patch
from testfixtures import TempDirectory
from provider.execution_context import S3Session
from tests.activity.classes_mock import FakeStorageContext
from tests import settings_mock


class TestS3Session(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("provider.execution_context.storage_context")
    def test_get_value(self, fake_storage_context):
        directory = TempDirectory()
        session_key = "session_key"
        test_value = {"foo": "bar"}
        fake_storage_context.return_value = FakeStorageContext(directory.path, [])
        s3_session_object = S3Session(settings_mock, test_value, session_key)
        self.assertEqual(s3_session_object.get_value("foo"), test_value.get("foo"))

    @patch("provider.execution_context.storage_context")
    def test_store_value(self, fake_storage_context):
        directory = TempDirectory()
        session_key = "session_key"
        key = "foo"
        value = "bar"
        fake_storage_context.return_value = FakeStorageContext(directory.path, [])
        s3_session_object = S3Session(settings_mock, None, session_key)
        s3_session_object.store_value(key, value)
        self.assertEqual(s3_session_object.get_value(key), value)
