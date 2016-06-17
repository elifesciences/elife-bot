import unittest
from activity.activity_PostEIFBridge import activity_PostEIFBridge
import settings_mock
import test_activity_data as data
from mock import mock, patch
from classes_mock import FakeSQSConn
from classes_mock import FakeSQSMessage
from classes_mock import FakeSQSQueue
import classes_mock
from testfixtures import TempDirectory
import json
import base64


class tests_PostEIFBridge(unittest.TestCase):
    def setUp(self):
        self.activity_PostEIFBridge = activity_PostEIFBridge(settings_mock, None, None, None, None)

    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PostEIFBridge.Message')
    def test_activity_published_article(self, mock_sqs_message, mock_sqs_connect):
        directory = TempDirectory()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        self.activity_PostEIFBridge.set_monitor_property = mock.MagicMock()
        self.activity_PostEIFBridge.emit_monitor_event = mock.MagicMock()
        success = self.activity_PostEIFBridge.do_activity(data.PostEIFBridge_data(True))
        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(data.PostEIFBridge_test_dir)
        self.assertEqual(True, success)
        self.assertEqual(json.dumps(data.PostEIFBridge_message), data_written_in_test_queue)

    #@patch.object(activity_PostEIFBridge, 'set_monitor_property')
    def test_activity_unpublished_article(self): #, mock_set_monitor_property
        #mock_set_monitor_property.side_effect = classes_mock.fake_monitor
        #self.activity_PostEIFBridge.set_monitor_property = mock.MagicMock(side_effect=classes_mock.fake_monitor)
        self.activity_PostEIFBridge.set_monitor_property = mock.MagicMock()
        self.activity_PostEIFBridge.emit_monitor_event = mock.MagicMock()
        success = self.activity_PostEIFBridge.do_activity(data.PostEIFBridge_data(False))
        self.assertEqual(True, success)
        #self.assertEqual(base64.decodestring(classes_mock.fake_monitor.value), data.PostEIFBridge_message)
        #add another assert with what has been added in through set_monitor_property


if __name__ == '__main__':
    unittest.main()
