import unittest
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.cron_FiveMinute import cron_FiveMinute
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from mock import patch


class TestCronFiveMinute(unittest.TestCase):
    def setUp(self):
        self.starter = cron_FiveMinute()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock))

    def test_get_starter_module_failure(self):
        "for coverage test failure"
        starter_name = 'not_a_starter'
        module_object = self.starter.get_starter_module(starter_name, FakeLogger())
        self.assertIsNone(module_object)

    def test_import_starter_module_failure(self):
        "for coverage test import failure"
        starter_name = 'not_a_starter'
        return_value = self.starter.import_starter_module(starter_name, FakeLogger())
        self.assertFalse(return_value)


if __name__ == '__main__':
    unittest.main()
