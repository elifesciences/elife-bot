import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_PubRouterDeposit import starter_PubRouterDeposit
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.starter = starter_PubRouterDeposit()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        workflow = 'HEFCE'
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, workflow))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        workflow = 'HEFCE'
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock, workflow))


if __name__ == '__main__':
    unittest.main()
