import unittest
import sys
from mock import patch
import starter.starter_FinishPreprintPublication as starter_module
from starter.starter_FinishPreprintPublication import (
    starter_FinishPreprintPublication as starter_object,
)
from starter.starter_helper import NullRequiredDataException
from tests import settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger


class TestStarterFinishPreprintPublication(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_object(settings_mock, self.logger)

    def test_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
        )

    @patch("boto3.client")
    def test_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.start(settings=settings_mock, article_id="353", version="1")

    @patch("boto3.client")
    def test_no_article_id(self, fake_client):
        "test if no article_id argument is specified"
        fake_client.return_value = FakeSWFClient()
        with self.assertRaises(Exception):
            self.starter.start(settings=settings_mock)

    @patch("boto3.client")
    def test_no_version(self, fake_client):
        "test if no version argument is specified"
        fake_client.return_value = FakeSWFClient()
        with self.assertRaises(Exception):
            self.starter.start(settings=settings_mock, article_id="353")

    @patch("boto3.client")
    def test_main(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        env = "dev"
        article_id = "7"
        version = "1"
        testargs = [
            "starter_FinishPreprintPublication.py",
            "-e",
            env,
            "-a",
            article_id,
            "-v",
            version,
        ]
        with patch.object(sys, "argv", testargs):
            # not too much can be asserted at this time, just test it returns None
            self.assertEqual(starter_module.main(), None)
