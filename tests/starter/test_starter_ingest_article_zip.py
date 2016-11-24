import unittest
from starter.starter_IngestArticleZip import starter_IngestArticleZip
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch

run_example = u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda'

class FakeBotoConnection:
    def start_workflow_execution(self, *args):
        pass


class TestStarterIngestArticleZip(unittest.TestCase):
    def setUp(self):
        self.stater_ingest_article_zip = starter_IngestArticleZip()

    def test_ingest_article_zip_starter_no_article(self):
        self.assertRaises(NullRequiredDataException, self.stater_ingest_article_zip.start,
                          settings=settings_mock, run=run_example, info=test_data.data_error_lax)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_ingest_article_zip_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_ingest_article_zip.start(settings=settings_mock, run=run_example,
                                             info=S3NotificationInfo.from_dict(test_data.ingest_article_zip_data))


if __name__ == '__main__':
    unittest.main()
