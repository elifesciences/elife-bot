import unittest
import starter.starter_DepositDOAJ as starter_module
from starter.starter_DepositDOAJ import starter_DepositDOAJ
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
from mock import patch
from tests.classes_mock import FakeBotoConnection
from tests.activity.classes_mock import FakeSession


class TestStarterDepositDOAJ(unittest.TestCase):
    def setUp(self):
        self.starter = starter_DepositDOAJ()

    @patch.object(starter_module, "get_session")
    def test_starter_no_article(self, mock_session):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run="",
            info={},
        )

    @patch.object(starter_module, "get_session")
    @patch("starter.starter_helper.get_starter_logger")
    @patch("boto.swf.layer1.Layer1")
    def test_deposit_doaj_start(self, fake_boto_conn, fake_logger, mock_session):
        fake_boto_conn.return_value = FakeBotoConnection()
        run = ""
        info = {"article_id": "00353"}
        self.starter.start(settings=settings_mock, run=run, info=info)
