import unittest
from ddt import ddt, data
from mock import patch
import activity.activity_IngestToLax as activity_module
from activity.activity_IngestToLax import activity_IngestToLax
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import (
    FakeLogger, FakeSession, FakeSQSConn, FakeSQSQueue, FakeSQSMessage)
from tests.activity import test_activity_data
from testfixtures import TempDirectory


data_example = {
    "article_id": "00353",
    "update_date": "2016-10-05T10:31:54Z",
    "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
    "message": None,
    "requested_action": "ingest",
    "result": "ingested",
    "run": "bb2d37b8-e73c-43b3-a092-d555753316af",
    "status": "vor",
    "version": "1",
    "run_type": "initial-article"
}

@ddt
class TestIngestToLax(unittest.TestCase):
    def setUp(self):
        self.ingesttolax = activity_IngestToLax(settings_mock, FakeLogger(), None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @data(data_example)
    @patch('boto.sqs.connect_to_region')
    @patch('boto.sqs.connection.SQSConnection.get_queue')
    @patch.object(activity_module, 'RawMessage')
    @patch('provider.lax_provider.prepare_action_message')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_IngestToLax, 'emit_monitor_event')
    def test_do_activity_success(self, data, fake_emit_monitor, fake_session, fake_action_message,
                                 fake_sqs_message, fake_sqs_queue, fake_sqs_conn):
        directory = TempDirectory()
        fake_action_message.return_value = {"example_message": True}
        fake_session.return_value = FakeSession(test_activity_data.data_example_before_publish)
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        fake_sqs_queue.return_value = FakeSQSQueue(directory)
        fake_sqs_message.return_value = FakeSQSMessage(directory)
        return_value = self.ingesttolax.do_activity(data)
        self.assertEqual(return_value, activity_IngestToLax.ACTIVITY_SUCCESS)

    @data(data_example)
    @patch('provider.lax_provider.prepare_action_message')
    def test_get_message_queue_success(self, data, fake_action_message):
        fake_action_message.return_value = {"example_message": True}

        message, queue, start_event, end_event, end_event_details, exception = self.ingesttolax.get_message_queue(data)
        self.assertEqual(queue, settings_mock.xml_info_queue)
        self.assertEqual(start_event, [settings_mock, data['article_id'], data['version'], data['run'],
                                       self.ingesttolax.pretty_name, "start",
                                       "Starting preparation of article for Lax " + data['article_id']])
        self.assertEqual(end_event, "end")
        self.assertEqual(end_event_details, [settings_mock, data['article_id'], data['version'], data['run'],
                                             self.ingesttolax.pretty_name, "end",
                                             "Finished preparation of article for Lax. "
                                             "Ingest sent to Lax" + data['article_id']])
        self.assertIsNone(exception)

    @data(data_example)
    @patch("provider.lax_provider.prepare_action_message")
    def test_get_message_queue_error(self, data, fake_lax_provider):
        fake_lax_provider.side_effect = Exception("Access Denied")
        message, queue, start_event, end_event, end_event_details, exception = self.ingesttolax.get_message_queue(data)
        self.assertEqual(end_event, "error")
        self.assertEqual(exception, "Access Denied")
        self.assertListEqual(end_event_details, [settings_mock, data['article_id'], data['version'], data['run'],
                                                 self.ingesttolax.pretty_name, "error",
                                                 "Error preparing or sending message to lax" + data['article_id'] +
                                                 " message: Access Denied"])


if __name__ == '__main__':
    unittest.main()
