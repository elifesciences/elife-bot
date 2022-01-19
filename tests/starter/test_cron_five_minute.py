import unittest
from mock import patch
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.cron_FiveMinute import cron_FiveMinute
from tests.classes_mock import FakeLayer1, FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock


class TestCronFiveMinute(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = cron_FiveMinute(settings_mock, logger=self.fake_logger)

    @patch("boto3.client")
    @patch("boto.swf.layer1.Layer1")
    def test_start(self, fake_conn, fake_client):
        fake_conn.return_value = FakeLayer1()
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos({"executionInfos": []})
        fake_client.return_value = mock_swf_client
        self.assertIsNone(self.starter.start(settings_mock))

    @patch("boto3.client")
    @patch.object(FakeLayer1, "start_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_exception(self, fake_conn, fake_start, fake_client):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError(
            "message", None
        )
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos({"executionInfos": []})
        fake_client.return_value = mock_swf_client
        self.assertIsNone(self.starter.start(settings_mock))
