import unittest
from activity.activity_PostEIFBridge import activity_PostEIFBridge
import settings_mock
import test_activity_data as data
from mock import mock, patch
from classes_mock import FakeSQSConn
from classes_mock import FakeSQSMessage
from classes_mock import FakeSQSQueue
from classes_mock import FakeMonitorProperty
from classes_mock import FakeLogger
from classes_mock import FakeEmitMonitorEvent
import classes_mock
from testfixtures import TempDirectory
import json


class tests_PostEIFBridge(unittest.TestCase):
    def setUp(self):
        self.activity_PostEIFBridge = activity_PostEIFBridge(settings_mock, None, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    @patch.object(activity_PostEIFBridge, 'set_monitor_property')
    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PostEIFBridge.Message')
    def test_activity_published_article(self, mock_sqs_message, mock_sqs_connect, mock_set_monitor_property, mock_emit_monitor_event):

        directory = TempDirectory()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)

        fake_monitor_property = FakeMonitorProperty()
        mock_set_monitor_property.side_effect = fake_monitor_property.set

        fake_monitor_event = FakeEmitMonitorEvent()
        mock_emit_monitor_event.side_effect = fake_monitor_event.set

        #When
        success = self.activity_PostEIFBridge.do_activity(data.PostEIFBridge_data(True))

        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(data.PostEIFBridge_test_dir)

        #Then
        self.assertEqual(True, success)

        self.assertEqual(json.dumps(data.PostEIFBridge_message), data_written_in_test_queue)
        self.assertEqual(fake_monitor_property.item_identifier, '00353')
        self.assertEqual(fake_monitor_property.name, 'publication-status')
        self.assertEqual(fake_monitor_property.value, 'published')
        self.assertEqual(fake_monitor_property.property_type, 'text')
        self.assertEqual(fake_monitor_property.version, '1')

        self.assertEqual(fake_monitor_event.item_identifier, '00353')
        self.assertEqual(fake_monitor_event.version, '1')
        self.assertEqual(fake_monitor_event.run, 'cf9c7e86-7355-4bb4-b48e-0bc284221251')
        self.assertEqual(fake_monitor_event.event_type, 'Post EIF Bridge')
        self.assertEqual(fake_monitor_event.status, 'end')
        self.assertEqual(fake_monitor_event.message, "Finished Post EIF Bridge 00353")

    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    @patch.object(activity_PostEIFBridge, 'set_monitor_property')
    def test_activity_unpublished_article(self, mock_set_monitor_property, mock_emit_monitor_event):

        fake_monitor_property = FakeMonitorProperty()
        mock_set_monitor_property.side_effect = fake_monitor_property.set

        fake_monitor_event = FakeEmitMonitorEvent()
        mock_emit_monitor_event.side_effect = fake_monitor_event.set

        #When
        success = self.activity_PostEIFBridge.do_activity(data.PostEIFBridge_data(False))

        #Then
        self.assertEqual(True, success)

        self.assertEqual(fake_monitor_property.item_identifier, '00353')
        self.assertEqual(fake_monitor_property.name, 'publication-status')
        self.assertEqual(fake_monitor_property.value, 'ready to publish')
        self.assertEqual(fake_monitor_property.property_type, 'text')
        self.assertEqual(fake_monitor_property.version, '1')

        self.assertEqual(fake_monitor_event.item_identifier, '00353')
        self.assertEqual(fake_monitor_event.version, '1')
        self.assertEqual(fake_monitor_event.run, 'cf9c7e86-7355-4bb4-b48e-0bc284221251')
        self.assertEqual(fake_monitor_event.event_type, 'Post EIF Bridge')
        self.assertEqual(fake_monitor_event.status, 'end')
        self.assertEqual(fake_monitor_event.message, "Finished Post EIF Bridge 00353")

    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    def test_activity_exception(self, mock_emit_monitor_event):

        fake_monitor_event = FakeEmitMonitorEvent()
        mock_emit_monitor_event.side_effect = fake_monitor_event.set

        fake_logger = FakeLogger()
        self.activity_PostEIFBridge_with_log = activity_PostEIFBridge(settings_mock, fake_logger, None, None, None)

        #When
        success = self.activity_PostEIFBridge_with_log.do_activity(data.PostEIFBridge_data(False))

        #Then
        self.assertRaises(Exception)
        self.assertEqual("Exception after submitting article EIF", fake_logger.logexception)

        self.assertEqual(fake_monitor_event.item_identifier, '00353')
        self.assertEqual(fake_monitor_event.version, '1')
        self.assertEqual(fake_monitor_event.run, 'cf9c7e86-7355-4bb4-b48e-0bc284221251')
        self.assertEqual(fake_monitor_event.event_type, 'Post EIF Bridge')
        self.assertEqual(fake_monitor_event.status, 'error')
        self.assertEqual(fake_monitor_event.message, "Error carrying over information after EIF For article 00353 message:'NoneType' object has no attribute 'get_queue'")

        self.assertEqual(False, success)

if __name__ == '__main__':
    unittest.main()
