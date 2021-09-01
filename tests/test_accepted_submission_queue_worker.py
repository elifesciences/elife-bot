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
from tests.classes_mock import FakeFlag, FakeS3Event
from tests.activity.classes_mock import FakeLogger, FakeSQSMessage, FakeSQSQueue


TEST_BUCKET_NAME = "prod-elife-accepted-submission-cleaning"
EXPECTED_STARTER_NAME = "IngestAcceptedSubmission"


class TestAcceptedSubmissionQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.worker = AcceptedSubmissionQueueWorker(settings_mock, self.logger)
        # override the sleep value for faster testing
        self.worker.sleep_seconds = 0.1

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("queue_worker.Message")
    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("accepted_submission_queue_worker.AcceptedSubmissionQueueWorker.queues")
    def test_work(self, mock_queues, mock_queue_read, mock_sqs_message):
        "test the main method of the class"
        directory = TempDirectory()
        # mock_sqs_connect = FakeSQSConn(directory)
        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        # create an S3 event message
        s3_event = FakeS3Event(bucket_name=TEST_BUCKET_NAME)
        mock_queue_read.return_value = s3_event
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
