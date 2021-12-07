import unittest
import json
from mock import patch
from provider.utils import unicode_encode
from provider.execution_context import S3Session
from tests.activity.classes_mock import FakeS3Connection
from tests import settings_mock


class TestS3Session(unittest.TestCase):
    @patch("provider.execution_context.S3Session.get_full_key")
    @patch("boto.s3.key.Key.get_contents_as_string")
    @patch("provider.execution_context.S3Connection")
    def test_get_value(
        self, fake_s3_connection, fake_get_contents_as_string, fake_get_full_key
    ):
        session_value = b'{"foo": "bar"}'
        expected = json.loads(unicode_encode(session_value))
        fake_get_full_key.return_value = None
        fake_s3_connection.return_value = FakeS3Connection()
        fake_get_contents_as_string.return_value = session_value
        s3_session_object = S3Session(settings_mock, None, None)
        self.assertEqual(s3_session_object.get_value(None), expected)


if __name__ == "__main__":
    unittest.main()
