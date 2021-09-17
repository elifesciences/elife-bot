import unittest
from mock import patch
from starter.starter_PubmedArticleDeposit import starter_PubmedArticleDeposit
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock


class TestStarterPubmedArticleDeposit(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_PubmedArticleDeposit(settings_mock, self.fake_logger)

    @patch("boto.swf.layer1.Layer1")
    def test_start(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock))

    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start_workflow())
