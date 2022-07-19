import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import execution_context
from provider.execution_context import FileSession, RedisSession, S3Session
from tests.classes_mock import FakeStrictRedis
from tests.activity.classes_mock import FakeStorageContext
from tests import settings_mock


class TestSettings:
    session_class = "FileSession"


class TestGetSession(unittest.TestCase):
    def test_get_session(self):
        "default value"
        result = execution_context.get_session(settings_mock, None, None)
        self.assertTrue(isinstance(result, RedisSession))

    def test_get_session_by_session_class(self):
        "test loading a session_class"

        result = execution_context.get_session(TestSettings(), None, None)
        self.assertTrue(isinstance(result, FileSession))


class TestFileSession(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.settings = TestSettings()
        # set the file path in the settings to the temporary directory path
        self.settings.workflow_context_path = self.directory.path

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_value(
        self,
    ):
        session_key = "session_key"
        test_value = {"foo": "bar"}
        file_session_object = FileSession(self.settings, test_value, session_key)
        self.assertEqual(file_session_object.get_value("foo"), test_value.get("foo"))

    def test_store_value(
        self,
    ):
        session_key = "session_key"
        key = "foo"
        value = "bar"
        file_session_object = FileSession(self.settings, None, session_key)
        file_session_object.store_value(key, value)
        self.assertEqual(file_session_object.get_value(key), value)


class TestRedisSession(unittest.TestCase):
    @patch("redis.StrictRedis")
    def test_get_value(self, fake_strict_redis):
        session_key = "session_key"
        test_value = {"foo": "bar"}
        fake_strict_redis.return_value = FakeStrictRedis()
        redis_session_object = RedisSession(settings_mock, test_value, session_key)
        self.assertEqual(redis_session_object.get_value("foo"), test_value.get("foo"))

    @patch("redis.StrictRedis")
    def test_store_value(self, fake_strict_redis):
        session_key = "session_key"
        key = "foo"
        value = "bar"
        fake_strict_redis.return_value = FakeStrictRedis()
        redis_session_object = RedisSession(settings_mock, None, session_key)
        redis_session_object.store_value(key, value)
        self.assertEqual(redis_session_object.get_value(key), value)


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
