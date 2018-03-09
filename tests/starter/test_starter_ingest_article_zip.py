import unittest
from starter.starter_IngestArticleZip import starter_IngestArticleZip
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from tests.classes_mock import FakeBotoConnection


class TestStarterIngestArticleZip(unittest.TestCase):
    def setUp(self):
        self.stater_ingest_article_zip = starter_IngestArticleZip()

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_ingest_article_zip_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_ingest_article_zip.start(settings=settings_mock, run=test_data.ingest_article_zip_data['run'],
                                             article_id=test_data.ingest_article_zip_data['article_id'],
                                             version_reason=test_data.ingest_article_zip_data['version_reason'],
                                             scheduled_publication_date=test_data.ingest_article_zip_data[
                                                 'scheduled_publication_date']
                                             )

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_ingest_article_zip_starter_novr_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_ingest_article_zip.start(settings=settings_mock, run=test_data.ingest_article_zip_no_vr_data['run'],
                                             article_id=test_data.ingest_article_zip_no_vr_data['article_id']
                                             )


if __name__ == '__main__':
    unittest.main()
