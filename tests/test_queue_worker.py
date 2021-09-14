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
from tests.classes_mock import FakeFlag, FakeS3Event
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSQSConn,
    FakeSQSMessage,
    FakeSQSQueue,
)


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.worker = QueueWorker(settings_mock, self.logger)
        # override the sleep value for faster testing
        self.worker.sleep_seconds = 0.1

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("queue_worker.Message")
    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("queue_worker.QueueWorker.queues")
    def test_work(self, mock_queues, mock_queue_read, mock_sqs_message):
        "test the main method of the class"
        directory = TempDirectory()
        # mock_sqs_connect = FakeSQSConn(directory)
        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        # create an S3 event message
        s3_event = FakeS3Event()
        mock_queue_read.return_value = s3_event
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(bytes_decode(directory.read("fake_sqs_body")))
        self.assertEqual(out_queue_message, test_data.queue_worker_starter_message)
        self.assertEqual(self.worker.logger.loginfo[-1], "graceful shutdown")

    @patch("queue_worker.Message")
    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("queue_worker.QueueWorker.queues")
    def test_work_unknown_bucket(self, mock_queues, mock_queue_read, mock_sqs_message):
        "test work method with an unrecognised bucket name"
        directory = TempDirectory()

        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        # create an S3 event message
        s3_event = FakeS3Event()
        # here override the bucket name
        s3_event._bucket_name = "not_a_real_bucket"
        mock_queue_read.return_value = s3_event
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertion, should be no message in the sqs queue
        out_queue_list = os.listdir(directory.path)
        self.assertEqual(out_queue_list, [])
        self.assertEqual(self.worker.logger.loginfo[-1], "graceful shutdown")

    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("queue_worker.QueueWorker.queues")
    def test_work_no_messages(self, mock_queues, mock_queue_read):
        "test work method with an unrecognised bucket name"
        directory = TempDirectory()
        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_queue_read.return_value = None
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        # assertion, should be a loginfo message
        self.assertEqual(self.worker.logger.loginfo[1], "reading message")
        self.assertEqual(self.worker.logger.loginfo[2], "no messages available")
        self.assertEqual(self.worker.logger.loginfo[3], "graceful shutdown")

    @patch("queue_worker.QueueWorker.queues")
    def test_work_no_queue(self, mock_queues):
        "test if queues are none"
        mock_queues.return_value = None, None
        self.worker.queues()
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.worker.work(flag)
        self.assertEqual(self.worker.logger.logerror, "error obtaining queue")

    @patch("boto.sqs.connect_to_region")
    def test_queues(self, fake_sqs_conn):
        "test code which connects to queues for coverage using mocked objects"
        # mock things
        directory = TempDirectory()
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        self.worker.queues()
        self.assertIsNotNone(self.worker.conn)


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
