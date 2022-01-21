import unittest
from mock import patch
from tests import settings_mock
from tests.classes_mock import FakeSWFClient
import register


class TestRegister(unittest.TestCase):
    @patch("boto3.client")
    def test_start(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(register.start(settings_mock))
