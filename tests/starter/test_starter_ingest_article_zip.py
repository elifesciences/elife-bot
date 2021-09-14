import unittest
from mock import patch
from starter.starter_IngestArticleZip import starter_IngestArticleZip
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
import tests.test_data as test_data

from tests.classes_mock import FakeBotoConnection


RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"


class TestStarterIngestArticleZip(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_IngestArticleZip(settings_mock, logger=self.fake_logger)

    def test_ingest_article_zip_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info={},
        )

    @patch("boto.swf.layer1.Layer1")
    def test_ingest_article_zip_starter(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.starter.start(
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=S3NotificationInfo.from_dict(test_data.ingest_article_zip_data),
        )

    @patch.object(starter_IngestArticleZip, "start_swf_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_ingest_article_zip_starter_exception(self, fake_boto_conn, fake_start):
        fake_boto_conn.return_value = FakeBotoConnection()
        fake_start.side_effect = Exception("An unhandled exception")
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(test_data.ingest_article_zip_data),
            )
        )

    @patch.object(starter_IngestArticleZip, "start_swf_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_ingest_article_zip_starter_null_required_exception(
        self, fake_boto_conn, fake_start
    ):
        fake_boto_conn.return_value = FakeBotoConnection()
        fake_start.side_effect = NullRequiredDataException(
            "NullRequiredDataException exception"
        )
        with self.assertRaises(NullRequiredDataException):
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(test_data.ingest_article_zip_data),
            )
