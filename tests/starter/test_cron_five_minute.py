import unittest
from mock import patch
from starter.cron_FiveMinute import cron_FiveMinute
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock


class TestCronFiveMinute(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = cron_FiveMinute(settings_mock, logger=self.fake_logger)

    @patch("boto3.client")
    def test_start(self, fake_client):
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos({"executionInfos": []})
        fake_client.return_value = mock_swf_client
        self.assertIsNone(self.starter.start(settings_mock))

    @patch("boto3.client")
    @patch.object(FakeSWFClient, "start_workflow_execution")
    def test_start_exception(self, fake_start, fake_client):
        mock_swf_client = FakeSWFClient()
        fake_start.side_effect = Exception()
        mock_swf_client.add_infos({"executionInfos": []})
        fake_client.return_value = mock_swf_client
        self.assertIsNone(self.starter.start(settings_mock))
