import unittest
from mock import patch
from starter.starter_IngestAcceptedSubmission import starter_IngestAcceptedSubmission
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.classes_mock import FakeBotoConnection


RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"


class TestStarterIngestAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_IngestAcceptedSubmission(
            settings_mock, logger=self.fake_logger
        )

    def test_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=test_data.data_error_lax,
        )

    @patch("boto.swf.layer1.Layer1")
    def test_starter(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )
        )

    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )
        )

    @patch.object(starter_IngestAcceptedSubmission, "start_swf_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow_null_exception(self, fake_boto_conn, fake_start):
        fake_boto_conn.return_value = FakeBotoConnection()
        fake_start.side_effect = NullRequiredDataException("An exception")
        with self.assertRaises(NullRequiredDataException):
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )

    @patch.object(starter_IngestAcceptedSubmission, "start_swf_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow_unhandled_exception(self, fake_boto_conn, fake_start):
        fake_boto_conn.return_value = FakeBotoConnection()
        fake_start.side_effect = Exception("An unhandled exception")
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )
        )
