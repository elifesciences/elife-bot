import unittest
from mock import patch
from starter.starter_helper import NullRequiredDataException
from starter.starter_PMCDeposit import starter_PMCDeposit
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeSWFClient
import tests.settings_mock as settings_mock


class TestStarterPMCDeposit(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_PMCDeposit(settings_mock, self.fake_logger)

    def test_start_no_document(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            document=None,
        )

    @patch("boto3.client")
    def test_start(self, fake_client):
        document = "document"
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(self.starter.start(settings_mock, document))
