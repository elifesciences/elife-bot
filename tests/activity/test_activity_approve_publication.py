import unittest
from activity.activity_ApprovePublication import activity_ApprovePublication
import settings_mock
import test_activity_data as activity_data
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
from ddt import ddt, data, unpack

@ddt
class tests_ApprovePublication(unittest.TestCase):
    def setUp(self):
        self.activity_ApprovePublication = activity_ApprovePublication(
            settings_mock, None, None, None, None)
        self.activity_ApprovePublication.logger = mock.MagicMock()
        self.activity_ApprovePublication.set_monitor_property = mock.MagicMock()
        self.activity_ApprovePublication.emit_monitor_event = mock.MagicMock()
 

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('requests.put')
    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_ApprovePublication.Message')
    @data(
        (200, None, {'update':'2012-12-13T00:00:00+00:00'}, "2012-12-13T00:00:00Z"),
        (200, "2015-12-13T00:00:00Z", {'update':'2012-12-13T00:00:00+00:00'}, "2015-12-13T00:00:00Z"),
        (200, None, {}, None),
    )
    @unpack
    def test_activity(self, status_code, response_update_date, update_json, expected_update_date,
                      mock_sqs_message, mock_sqs_connect, mock_requests_put):
        directory = TempDirectory()

        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        mock_requests_put.return_value = classes_mock.FakeResponse(status_code, update_json)

        success = self.activity_ApprovePublication.do_activity(
            activity_data.ApprovePublication_data(response_update_date))

        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(activity_data.ApprovePublication_test_dir)

        self.assertEqual(True, success)

        output_json = json.loads(directory.read(activity_data.ApprovePublication_test_dir))
        expected = activity_data.ApprovePublication_json_output_return_example(expected_update_date)
        self.assertDictEqual(output_json, expected)

    @patch('requests.put')
    def test_retry(self, mock_requests_put):
        mock_requests_put.return_value = classes_mock.FakeResponse(500, {})
        result = self.activity_ApprovePublication.do_activity(
            activity_data.ApprovePublication_data(None))
        self.assertEqual("ActivityTemporaryFailure", result)



if __name__ == '__main__':
    unittest.main()
