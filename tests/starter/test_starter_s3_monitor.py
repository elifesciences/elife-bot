import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_S3Monitor import starter_S3Monitor
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterS3Monitor(unittest.TestCase):
    def setUp(self):
        self.starter = starter_S3Monitor()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        workflow = 'S3Monitor'
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, workflow))

    @patch('boto.swf.layer1.Layer1')
    def test_start_poa(self, fake_conn):
        workflow = 'S3Monitor_POA'
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, workflow))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock))


if __name__ == '__main__':
    unittest.main()
