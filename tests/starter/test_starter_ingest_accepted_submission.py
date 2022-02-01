import unittest
from mock import patch
from starter.starter_IngestAcceptedSubmission import starter_IngestAcceptedSubmission
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.classes_mock import FakeSWFClient


RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"


class TestStarterIngestAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_IngestAcceptedSubmission(settings_mock, self.fake_logger)

    def test_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=test_data.data_error_lax,
        )

    @patch("boto3.client")
    def test_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(
            self.starter.start(
                settings=settings_mock,
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )
        )

    @patch("boto3.client")
    def test_start_workflow(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(
            self.starter.start_workflow(
                run=RUN_EXAMPLE,
                info=S3NotificationInfo.from_dict(
                    test_data.ingest_accepted_submission_data
                ),
            )
        )
