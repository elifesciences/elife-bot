import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_FTPArticle import starter_FTPArticle
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterFTPArticle(unittest.TestCase):
    def setUp(self):
        self.starter = starter_FTPArticle()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        workflow = 'HEFCE'
        doi_id = 3
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, workflow, doi_id))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        workflow = 'HEFCE'
        doi_id = 3
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock, workflow, doi_id))


if __name__ == '__main__':
    unittest.main()
