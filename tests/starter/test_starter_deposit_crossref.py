import unittest
from mock import patch
from starter.starter_DepositCrossref import starter_DepositCrossref
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeSWFClient
import tests.settings_mock as settings_mock


class TestStarterDepositCrossref(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_DepositCrossref(settings_mock, self.fake_logger)

    @patch("boto3.client")
    def test_start(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(self.starter.start(settings_mock))

    @patch("boto3.client")
    def test_start_workflow(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(self.starter.start_workflow())
