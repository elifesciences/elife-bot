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
        self.assertDictEqual(fake_monitor_property.monitor_data, self.monitor_property_expected_data("published"))

        self.assertDictEqual(fake_monitor_event.monitor_data,
                         self.monitor_event_expected_data("end", "Finished Post EIF Bridge 00353"))

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

        self.assertDictEqual(fake_monitor_property.monitor_data, self.monitor_property_expected_data("ready to publish"))

        self.assertDictEqual(fake_monitor_event.monitor_data,
                         self.monitor_event_expected_data("end", "Finished Post EIF Bridge 00353"))

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

        self.assertDictEqual(fake_monitor_event.monitor_data,
                         self.monitor_event_expected_data("error","Error carrying over information after EIF For "
                                                                  "article 00353 message:'NoneType' object has no "
                                                                  "attribute 'get_queue'"))

        self.assertEqual(False, success)

    def monitor_property_expected_data(self, value):
        return {'item_identifier': '00353',
                'name': 'publication-status',
                'value': value,
                'property_type': 'text',
                'version': '1'}

    def monitor_event_expected_data(self, status, message):
        return {'item_identifier': '00353',
                'version': '1',
                'run': 'cf9c7e86-7355-4bb4-b48e-0bc284221251',
                'event_type': 'Post EIF Bridge',
                'status': status,
                'message': message }

if __name__ == '__main__':
    unittest.main()
