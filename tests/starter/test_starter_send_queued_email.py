import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_SendQueuedEmail import starter_SendQueuedEmail
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterSendQueuedEmail(unittest.TestCase):
    def setUp(self):
        self.starter = starter_SendQueuedEmail()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        limit = None
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, limit))

    @patch('boto.swf.layer1.Layer1')
    def test_start_limit(self, fake_conn):
        limit = 5
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, limit))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock))


if __name__ == '__main__':
    unittest.main()
