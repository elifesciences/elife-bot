import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_PackagePOA import starter_PackagePOA
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterPackagePOA(unittest.TestCase):
    def setUp(self):
        self.starter = starter_PackagePOA()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        document = 'document'
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, document))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        document = 'document'
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock, document))


if __name__ == '__main__':
    unittest.main()
