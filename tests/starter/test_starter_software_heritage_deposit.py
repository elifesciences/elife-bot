import copy
import unittest
from mock import patch
from starter.starter_SoftwareHeritageDeposit import starter_SoftwareHeritageDeposit
from starter.starter_helper import NullRequiredDataException
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeBotoConnection


RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"

INFO_EXAMPLE = {
    "doi_id": "00666",
    "download_url": "https://example.org/api/projects/1/snapshots/1/archive",
}


class TestStarterSoftwareHeritageDeposit(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_SoftwareHeritageDeposit(
            settings_mock, logger=self.fake_logger
        )

    def test_software_heritage_deposit_starter_no_info(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info={},
        )

    def test_software_heritage_deposit_starter_info_missing_doi_id(self):
        info = copy.copy(INFO_EXAMPLE)
        del info["doi_id"]
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=info,
        )

    @patch("boto.swf.layer1.Layer1")
    def test_ingest_decision_letter_starter_no_run_argument(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=None,
                info=INFO_EXAMPLE,
            )
        )

    @patch("boto.swf.layer1.Layer1")
    def test_ingest_decision_letter_starter(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=RUN_EXAMPLE,
                info=INFO_EXAMPLE,
            )
        )

    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=INFO_EXAMPLE,
            )
        )
