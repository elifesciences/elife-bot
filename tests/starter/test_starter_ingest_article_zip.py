import unittest
from starter.starter_IngestArticleZip import starter_IngestArticleZip
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from tests.classes_mock import FakeBotoConnection


RUN_EXAMPLE = u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda'


class TestStarterIngestArticleZip(unittest.TestCase):
    def setUp(self):
        self.starter = starter_IngestArticleZip()

    def test_ingest_article_zip_starter_no_article(self):
        self.assertRaises(NullRequiredDataException, self.starter.start,
                          settings=settings_mock, run=RUN_EXAMPLE, info=test_data.data_error_lax)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_ingest_article_zip_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.starter.start(settings=settings_mock, run=RUN_EXAMPLE,
                                             info=S3NotificationInfo.from_dict(test_data.ingest_article_zip_data))
