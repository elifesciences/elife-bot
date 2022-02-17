import unittest
import json
import copy
from mock import patch
from testfixtures import TempDirectory
from accepted_submission_queue_worker import AcceptedSubmissionQueueWorker
from queue_worker import get_starter_name
from S3utility.s3_notification_info import S3NotificationInfo
from provider.utils import bytes_decode
from tests import settings_mock, test_data
from tests.classes_mock import FakeFlag
from tests.activity.classes_mock import FakeLogger, FakeSQSClient, FakeSQSQueue


TEST_BUCKET_NAME = "prod-elife-accepted-submission-cleaning"
EXPECTED_STARTER_NAME = "IngestAcceptedSubmission"


class TestAcceptedSubmissionQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.worker = AcceptedSubmissionQueueWorker(settings_mock, self.logger)
        # override the sleep value for faster testing
        self.worker.sleep_seconds = 0.001

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_work(self, mock_sqs_client):
        "test the main method of the class"
        directory = TempDirectory()
        # create an S3 event message
        records = test_data.test_s3_event_records(bucket=TEST_BUCKET_NAME)
        fake_queue_messages = [{"Messages": [{"Body": json.dumps(records)}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.accepted_submission_queue: FakeSQSQueue(
                directory, fake_queue_messages
            )
        }
        mock_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(bytes_decode(directory.read("fake_sqs_body")))
        self.assertEqual(out_queue_message.get("workflow_name"), EXPECTED_STARTER_NAME)
        self.assertEqual(self.worker.logger.loginfo[-1], "graceful shutdown")
        self.assertIsNotNone(self.worker.input_queue_name)


class TestAcceptedSubmissionGetStarterName(unittest.TestCase):
    def test_get_starter_name(self):
        "test rules matching to the S3 notification info"
        rules = test_data.queue_worker_rules
        data = copy.copy(test_data.queue_worker_article_zip_data)
        data["bucket_name"] = TEST_BUCKET_NAME
        info = S3NotificationInfo.from_dict(data)
        starter_name = get_starter_name(rules, info)
        self.assertEqual(starter_name, EXPECTED_STARTER_NAME)
