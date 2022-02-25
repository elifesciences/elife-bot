import os
import unittest
import json
from mock import patch
from testfixtures import TempDirectory
from queue_worker import QueueWorker
from queue_worker import load_rules, get_starter_name
from S3utility.s3_notification_info import S3NotificationInfo
from provider.utils import bytes_decode
from tests import settings_mock, test_data
from tests.classes_mock import FakeFlag
from tests.activity.classes_mock import FakeLogger, FakeSQSClient, FakeSQSQueue


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.worker = QueueWorker(settings_mock, self.logger)
        # override the sleep value for faster testing
        self.worker.sleep_seconds = 0.001

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_work(self, mock_sqs_client):
        "test the main method of the class"
        directory = TempDirectory()
        # create an S3 event message
        records = test_data.test_s3_event_records()
        fake_queue_messages = [{"Messages": [{"Body": json.dumps(records)}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.S3_monitor_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
            settings_mock.workflow_starter_queue: FakeSQSQueue(directory),
        }
        mock_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # expected queue message
        expected_starter_message = {
            "workflow_name": "IngestAcceptedSubmission",
            "workflow_data": {
                "event_name": "ObjectCreated:CompleteMultipartUpload",
                "event_time": "2022-02-09T01:43:07.709Z",
                "bucket_name": "continuumtest-elife-accepted-submission-cleaning",
                "file_name": "02-09-2022-RA-eLife-99999.zip",
                "file_etag": "28b76c025ab9bd3a967885302d413efa-3",
                "file_size": 19464507,
            },
        }
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(bytes_decode(directory.read("fake_sqs_body")))
        self.assertDictEqual(out_queue_message, expected_starter_message)
        self.assertEqual(self.worker.logger.loginfo[-1], "graceful shutdown")

    @patch("boto3.client")
    def test_work_unknown_bucket(self, mock_sqs_client):
        "test work method with an unrecognised bucket name"
        directory = TempDirectory()
        # create an S3 event message with a different bucket name
        records = test_data.test_s3_event_records(bucket="not_a_real_bucket")
        fake_queue_messages = [{"Messages": [{"Body": json.dumps(records)}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.S3_monitor_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
        }
        mock_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertion, should be no message in the sqs queue
        out_queue_list = os.listdir(directory.path)
        self.assertEqual(out_queue_list, [])
        self.assertEqual(self.worker.logger.loginfo[-1], "graceful shutdown")

    @patch("tests.activity.classes_mock.FakeSQSClient.receive_message")
    @patch("boto3.client")
    def test_work_no_messages(self, mock_sqs_client, mock_receive):
        "test empty receive_message return value"
        directory = TempDirectory()
        mock_sqs_client.return_value = FakeSQSClient(directory)
        mock_receive.return_value = {}
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertion, should be a loginfo message
        self.assertEqual(self.worker.logger.loginfo[1], "reading message")
        self.assertEqual(self.worker.logger.loginfo[2], "no messages available")
        self.assertEqual(self.worker.logger.loginfo[3], "graceful shutdown")

    @patch("queue_worker.QueueWorker.queues")
    @patch("boto3.client")
    def test_work_no_queue(self, mock_sqs_client, mock_queues):
        "test if queues are none"
        mock_sqs_client.return_value = FakeSQSClient()
        mock_queues.return_value = None, None
        self.worker.queues()
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        self.assertEqual(self.worker.logger.logerror, "error obtaining queue")


class TestQueueWorkerLogInit(unittest.TestCase):
    def test_queue_worker_init(self):
        "test object instantiation without passing in a log object"
        worker = QueueWorker(settings_mock)
        self.assertIsNotNone(worker.logger)


class TestLoadRules(unittest.TestCase):
    def test_load_rules(self):
        "test loading rules YAML file"
        rules = load_rules()
        self.assertIsNotNone(rules)


class TestGetStarterName(unittest.TestCase):
    def test_get_starter_name(self):
        "test rules matching to the S3 notification info"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.queue_worker_article_zip_data)
        expected_starter_name = "IngestArticleZip"
        starter_name = get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)

    def test_get_starter_name_ingest_digest(self):
        "test S3 notification info matching for the ingest digest workflow"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.ingest_digest_data)
        expected_starter_name = "IngestDigest"
        starter_name = get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)

    def test_get_starter_name_ingest_decision_letter(self):
        "test S3 notification info matching for the ingest decision letter workflow"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.ingest_decision_letter_data)
        expected_starter_name = "IngestDecisionLetter"
        starter_name = get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)
