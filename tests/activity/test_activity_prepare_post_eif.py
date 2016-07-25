import unittest
from activity.activity_PreparePostEIF import activity_PreparePostEIF
import settings_mock
import test_activity_data as data
from mock import mock, patch
from classes_mock import FakeSession
from classes_mock import FakeSQSConn
from classes_mock import FakeSQSMessage
from classes_mock import FakeSQSQueue
from classes_mock import FakeKey
from classes_mock import FakeS3Connection
import classes_mock
from testfixtures import TempDirectory
import json
import base64


class tests_PreparePostEIF(unittest.TestCase):
    def setUp(self):
        self.activity_PreparePostEIF = activity_PreparePostEIF(settings_mock, None, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PreparePostEIF.Message')
    @patch('activity.activity_PreparePostEIF.Key')
    @patch('activity.activity_PreparePostEIF.S3Connection')
    @patch('activity.activity_PreparePostEIF.Session')
    def test_activity(self, fake_session_mock, fake_s3_mock, fake_key_mock,
                      mock_sqs_message, mock_sqs_connect):
        directory = TempDirectory()
        fake_session_mock.return_value = FakeSession(data.PreparePost_session_example)
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        fake_s3_mock.return_value = FakeS3Connection()
        self.activity_PreparePostEIF.logger = mock.MagicMock()
        self.activity_PreparePostEIF.set_monitor_property = mock.MagicMock()
        self.activity_PreparePostEIF.emit_monitor_event = mock.MagicMock()

        success = self.activity_PreparePostEIF.do_activity()

        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(data.PreparePostEIF_test_dir)

        self.assertEqual(True, success)
        self.assertEqual(json.dumps(data.PreparePostEIF_message), data_written_in_test_queue)

        output_json = json.loads(directory.read(data.PreparePostEIF_test_dir))
        expected = data.PreparePostEIF_json_output_return_example
        self.assertDictEqual(output_json, expected)

if __name__ == '__main__':
    unittest.main()
