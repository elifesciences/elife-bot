# coding=utf-8
import unittest
from mock import patch
from provider import sts
from tests import settings_mock
from tests.activity.classes_mock import FakeStsClient


class TestGetClient(unittest.TestCase):
    "tests for get_client()"

    @patch("boto3.client")
    def test_get_client(self, fake_sts_client):
        "test getting STS client"
        fake_sts_client.return_value = FakeStsClient()
        # invoke
        result = sts.get_client(settings_mock)
        # assert
        self.assertIsNotNone(result)


class TestAssumeRole(unittest.TestCase):
    "tests for assume_role()"

    def test_assume_role(self):
        "test assuming role from STS client"
        client = FakeStsClient()
        role_arn = "arn"
        role_session_name = "session_name"
        # invoke
        result = sts.assume_role(client, role_arn, role_session_name)
        # assert
        self.assertTrue("Credentials" in result)
