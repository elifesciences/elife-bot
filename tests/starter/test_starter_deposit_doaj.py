import unittest
import starter.starter_DepositDOAJ as starter_module
from starter.starter_DepositDOAJ import starter_DepositDOAJ
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
from mock import patch
from tests.classes_mock import FakeBotoConnection


class TestStarterDepositDOAJ(unittest.TestCase):
    def setUp(self):
        self.starter = starter_DepositDOAJ()

    def test_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            info={},
        )

    @patch("starter.starter_helper.get_starter_logger")
    @patch("boto.swf.layer1.Layer1")
    def test_deposit_doaj_start(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        info = {"article_id": "00353"}
        self.starter.start(settings=settings_mock, info=info)
