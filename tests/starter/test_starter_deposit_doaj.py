import unittest
from mock import patch
from starter.starter_DepositDOAJ import starter_DepositDOAJ
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeSWFClient


class TestStarterDepositDOAJ(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_DepositDOAJ(settings_mock, self.fake_logger)

    def test_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            info={},
        )

    @patch("boto3.client")
    def test_start_workflow_no_article_id(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        info = {"article_id": ""}
        with self.assertRaises(NullRequiredDataException):
            self.starter.start(settings=settings_mock, info=info)

    @patch("boto3.client")
    def test_deposit_doaj_start(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        info = {"article_id": "353"}
        self.starter.start(settings=settings_mock, info=info)
