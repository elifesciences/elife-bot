import unittest
from starter.starter_CopyGlencoeStillImages import starter_CopyGlencoeStillImages
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from tests.classes_mock import FakeBotoConnection


class TestStarterCopyGlencoeStillImages(unittest.TestCase):
    def setUp(self):
        self.stater_copy_glencoe_still_images = starter_CopyGlencoeStillImages()

    def test_copy_glencoe_still_images_starter_no_article(self):
        self.assertRaises(NullRequiredDataException, self.stater_copy_glencoe_still_images.start,
                          settings=settings_mock)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_copy_glencoe_still_images_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_copy_glencoe_still_images.start(settings=settings_mock, article_id='00353')


if __name__ == '__main__':
    unittest.main()
