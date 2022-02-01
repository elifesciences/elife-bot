import unittest
import sys
from mock import patch
import starter.starter_CopyGlencoeStillImages as starter_module
from starter.starter_CopyGlencoeStillImages import starter_CopyGlencoeStillImages
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger


class TestStarterCopyGlencoeStillImages(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_CopyGlencoeStillImages(settings_mock, self.logger)

    def test_copy_glencoe_still_images_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
        )

    @patch("boto3.client")
    def test_copy_glencoe_still_images_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.start(settings=settings_mock, article_id="353")

    @patch("boto3.client")
    def test_main(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        env = "dev"
        doi_id = "7"
        testargs = ["starter_CopyGlencoeStillImages.py", "-e", env, "-a", doi_id, "-p"]
        with patch.object(sys, "argv", testargs):
            # not too much can be asserted at this time, just test it returns None
            self.assertEqual(starter_module.main(), None)
