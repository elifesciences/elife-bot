import copy
import unittest
from mock import patch
from starter.starter_SoftwareHeritageDeposit import starter_SoftwareHeritageDeposit
from starter.starter_helper import NullRequiredDataException
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeSWFClient


RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"

INFO_EXAMPLE = {
    "article_id": "666",
    "input_file": "https://example.org/api/projects/1/snapshots/1/archive",
}


class TestStarterSoftwareHeritageDeposit(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_SoftwareHeritageDeposit(settings_mock, self.fake_logger)

    def test_software_heritage_start_no_info(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info={},
        )

    def test_software_heritage_start_info_missing_article_id(self):
        info = copy.copy(INFO_EXAMPLE)
        del info["article_id"]
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=info,
        )

    @patch("boto3.client")
    def test_software_heritage_start_no_run_argument(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=None,
                info=INFO_EXAMPLE,
            )
        )

    @patch("boto3.client")
    def test_software_heritage_start(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=RUN_EXAMPLE,
                info=INFO_EXAMPLE,
            )
        )

    @patch("boto3.client")
    def test_start_workflow(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=INFO_EXAMPLE,
            )
        )
