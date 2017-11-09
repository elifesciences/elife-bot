import unittest
from activity.activity_PreparePostEIF import activity_PreparePostEIF
import settings_mock
import test_activity_data as test_data
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
        self.activity_PreparePostEIF = activity_PreparePostEIF(
            settings_mock, None, None, None, None)

        self.do_activity_passes = []
        activity_pass = {
            "update_date": "2012-12-13T00:00:00Z",
            "message": test_data.PreparePostEIF_message,
            "expected": test_data.PreparePostEIF_json_output_return_example
        }
        # activity_pass = {
        #     "update_date": None,
        #     "message": test_data.PreparePostEIF_message_no_update_date,
        #     "expected": test_data.PreparePostEIF_json_output_return_example_no_update_date
        # }
        self.do_activity_passes.append(activity_pass)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PreparePostEIF.Message')
    @patch('activity.activity_PreparePostEIF.Key')
    @patch('activity.activity_PreparePostEIF.S3Connection')
    @patch('activity.activity_PreparePostEIF.get_session')
    def test_activity(self, fake_session_mock, fake_s3_mock, fake_key_mock,
                      mock_sqs_message, mock_sqs_connect):
        directory = TempDirectory()

        for testdata in self.do_activity_passes:

            fake_session_mock.return_value = FakeSession(test_data.PreparePost_session_example(
                testdata["update_date"]))
            mock_sqs_connect.return_value = FakeSQSConn(directory)
            mock_sqs_message.return_value = FakeSQSMessage(directory)
            fake_s3_mock.return_value = FakeS3Connection()
            self.activity_PreparePostEIF.logger = mock.MagicMock()
            self.activity_PreparePostEIF.set_monitor_property = mock.MagicMock()
            self.activity_PreparePostEIF.emit_monitor_event = mock.MagicMock()

            success = self.activity_PreparePostEIF.do_activity(test_data.PreparePostEIF_data)

            fake_sqs_queue = FakeSQSQueue(directory)
            data_written_in_test_queue = fake_sqs_queue.read(test_data.PreparePostEIF_test_dir)

            self.assertEqual(True, success)
            self.assertEqual(json.dumps(testdata["message"]), data_written_in_test_queue)

            output_json = json.loads(directory.read(test_data.PreparePostEIF_test_dir))
            expected = testdata["expected"]
            self.assertDictEqual(output_json, expected)

if __name__ == '__main__':
    unittest.main()
