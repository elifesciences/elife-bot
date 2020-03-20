import unittest
from mock import patch
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_PubmedArticleDeposit import starter_PubmedArticleDeposit
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock


class TestStarterPubmedArticleDeposit(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_PubmedArticleDeposit(settings_mock, logger=self.fake_logger)

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock))

    @patch('boto.swf.layer1.Layer1')
    def test_start_workflow(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start_workflow())

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock))


if __name__ == '__main__':
    unittest.main()
