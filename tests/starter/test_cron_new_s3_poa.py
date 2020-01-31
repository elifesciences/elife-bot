import unittest
from mock import patch
from testfixtures import TempDirectory
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
import starter.cron_NewS3POA as starter_module
from starter.cron_NewS3POA import cron_NewS3POA
from tests.classes_mock import FakeLayer1, FakeS3Event
from tests.activity.classes_mock import FakeSQSConn, FakeSQSQueue
import tests.settings_mock as settings_mock


class TestCronNewS3POA(unittest.TestCase):
    def setUp(self):
        self.starter = cron_NewS3POA()

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('tests.activity.classes_mock.FakeSQSQueue.get_messages')
    @patch.object(starter_module, 'get_sqs_queue')
    @patch.object(starter_module, 'sqs_connect')
    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn, mock_sqs_connect, mock_queue, mock_get_messages):
        directory = TempDirectory()
        fake_conn.return_value = FakeLayer1()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        s3_event = FakeS3Event()
        mock_get_messages.return_value = [s3_event]
        self.assertIsNone(self.starter.start(settings_mock))

    @patch('tests.activity.classes_mock.FakeSQSQueue.get_messages')
    @patch.object(starter_module, 'get_sqs_queue')
    @patch.object(starter_module, 'sqs_connect')
    @patch('boto.swf.layer1.Layer1')
    def test_start_items(self, fake_conn, mock_sqs_connect, mock_queue, mock_get_messages):
        directory = TempDirectory()
        fake_conn.return_value = FakeLayer1()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        mock_get_messages.return_value = []
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('tests.activity.classes_mock.FakeSQSQueue.get_messages')
    @patch.object(starter_module, 'get_sqs_queue')
    @patch.object(starter_module, 'sqs_connect')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, mock_sqs_connect, mock_queue,
                             mock_get_messages, fake_start):
        directory = TempDirectory()
        fake_conn.return_value = FakeLayer1()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        mock_get_messages.return_value = []
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock))


if __name__ == '__main__':
    unittest.main()
