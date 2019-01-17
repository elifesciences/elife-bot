import unittest
import json
import boto.swf.layer1
from mock import patch
from testfixtures import TempDirectory
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeFlag, FakeBotoConnection
from tests.activity.classes_mock import FakeSQSMessage, FakeSQSQueue, FakeLogger
import queue_workflow_starter


class TestQueueWorkflowStarter(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('tests.activity.classes_mock.FakeSQSQueue.get_messages')
    @patch('queue_workflow_starter.get_queue')
    @patch.object(boto.swf.layer1, 'Layer1')
    def test_main(self, fake_boto_conn, mock_queue, mock_queue_read):
        directory = TempDirectory()
        message_body = json.dumps(
            {
                'workflow_name': 'Ping',
                'workflow_data': {}
            }
        )
        mock_boto_connection = FakeBotoConnection()
        fake_boto_conn.return_value = mock_boto_connection
        mock_queue.return_value = FakeSQSQueue(directory)
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        mock_queue_read.return_value = [fake_message]
        queue_workflow_starter.main(settings_mock, FakeFlag())
        self.assertEqual(mock_boto_connection.start_called, True)

    @patch.object(boto.swf.layer1, 'Layer1')
    def test_process_message(self, fake_boto_conn):
        directory = TempDirectory()
        message_body = json.dumps(
            {
                'workflow_name': 'PubmedArticleDeposit',
                'workflow_data': {}
            }
        )
        mock_boto_connection = FakeBotoConnection()
        fake_boto_conn.return_value = mock_boto_connection
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(settings_mock, FakeLogger(), fake_message)
        self.assertEqual(mock_boto_connection.start_called, True)

    @patch.object(boto.swf.layer1, 'Layer1')
    def test_process_message_no_data_processor(self, fake_boto_conn):
        directory = TempDirectory()
        message_body = json.dumps(
            {
                'workflow_name': 'Ping',
                'workflow_data': {}
            }
        )
        mock_boto_connection = FakeBotoConnection()
        fake_boto_conn.return_value = mock_boto_connection
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(settings_mock, FakeLogger(), fake_message)
        self.assertEqual(mock_boto_connection.start_called, True)

    @patch.object(boto.swf.layer1, 'Layer1')
    def test_process_message_fail_to_start_workflow(self, fake_boto_conn):
        directory = TempDirectory()
        message_body = json.dumps(
            {
                'workflow_name': 'not_a_real_workflow',
                'workflow_data': {}
            }
        )
        mock_boto_connection = FakeBotoConnection()
        fake_boto_conn.return_value = mock_boto_connection
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(settings_mock, FakeLogger(), fake_message)
        self.assertEqual(mock_boto_connection.start_called, None)

    def test_process_data_ingestarticlezip(self):
        workflow_name = ''
        workflow_data = {
            'article_id': '',
            'run': '',
            'version_reason': '',
            'scheduled_publication_date': '',
        }
        data = queue_workflow_starter.process_data_ingestarticlezip(workflow_name, workflow_data)
        self.assertEqual(sorted(data), sorted(workflow_data))

    def test_process_data_initialarticlezip(self):
        workflow_name = ''
        workflow_data = {
            'event_name': '',
            'event_time': '',
            'bucket_name': '',
            'file_name': '',
            'file_etag': '',
            'file_size': '',
        }
        data = queue_workflow_starter.process_data_initialarticlezip(workflow_name, workflow_data)
        s3_notification_dict = data.get("info").to_dict()
        self.assertEqual(sorted(s3_notification_dict), sorted(workflow_data))
        self.assertIsNotNone(data.get('run'))

    def test_process_data_postperfectpublication(self):
        workflow_name = ''
        workflow_data = {
            'some': 'data'
        }
        data = queue_workflow_starter.process_data_postperfectpublication(
            workflow_name, workflow_data)
        self.assertEqual(sorted(data.get('info')), sorted(workflow_data))

    def test_process_data_ingestdigest(self):
        workflow_name = ''
        workflow_data = {
            'event_name': '',
            'event_time': '',
            'bucket_name': '',
            'file_name': '',
            'file_etag': '',
            'file_size': '',
        }
        data = queue_workflow_starter.process_data_ingestdigest(workflow_name, workflow_data)
        s3_notification_dict = data.get("info").to_dict()
        self.assertEqual(sorted(s3_notification_dict), sorted(workflow_data))
        self.assertIsNotNone(data.get('run'))


if __name__ == '__main__':
    unittest.main()
