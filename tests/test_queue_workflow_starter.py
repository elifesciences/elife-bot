import unittest
import json
import boto.swf.layer1
from mock import patch
from testfixtures import TempDirectory
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeFlag, FakeBotoConnection
from tests.activity.classes_mock import FakeSQSMessage, FakeSQSQueue
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
        env = 'dev'
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
        # create a fake green flag
        flag = FakeFlag()
        queue_workflow_starter.main(settings_mock, env, flag)
        self.assertEqual(mock_boto_connection.start_called, True)


if __name__ == '__main__':
    unittest.main()
