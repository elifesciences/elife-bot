import sys
import unittest
from mock import patch
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.objects import Starter
import starter.cron_FiveMinute as starter_module
from starter.cron_FiveMinute import cron_FiveMinute
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock


class TestCronFiveMinute(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = cron_FiveMinute(settings_mock, logger=self.fake_logger)

    @patch("boto.swf.layer1.Layer1")
    def test_start(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeLayer1, "start_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError(
            "message", None
        )
        self.assertIsNone(self.starter.start(settings_mock))
