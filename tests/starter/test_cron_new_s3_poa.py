import unittest
from provider.simpleDB import SimpleDB
from provider.swfmeta import SWFMeta
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.cron_NewS3POA import cron_NewS3POA
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from mock import patch


class TestCronNewS3POA(unittest.TestCase):
    def setUp(self):
        self.starter = cron_NewS3POA()

    @patch.object(SimpleDB, 'elife_get_generic_delivery_S3_file_items')
    @patch.object(SWFMeta, 'get_last_completed_workflow_execution_startTimestamp')
    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn, fake_timestamp, fake_query):
        fake_conn.return_value = FakeLayer1()
        fake_timestamp.return_value = 0
        fake_query.return_value = []
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(SimpleDB, 'elife_get_generic_delivery_S3_file_items')
    @patch.object(SWFMeta, 'get_last_completed_workflow_execution_startTimestamp')
    @patch('boto.swf.layer1.Layer1')
    def test_start_items(self, fake_conn, fake_timestamp, fake_query):
        fake_conn.return_value = FakeLayer1()
        fake_timestamp.return_value = 0
        fake_query.return_value = [1]
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(SimpleDB, 'elife_get_generic_delivery_S3_file_items')
    @patch.object(SWFMeta, 'get_last_completed_workflow_execution_startTimestamp')
    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start, fake_timestamp, fake_query):
        fake_conn.return_value = FakeLayer1()
        fake_timestamp.return_value = 0
        fake_query.return_value = []
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
