import unittest
import json
from mock import Mock, patch
import tests.settings_mock as settings_mock
from queue_worker import QueueWorker
from S3utility.s3_notification_info import S3NotificationInfo
from provider.utils import unicode_decode
import tests.test_data as test_data
from tests.classes_mock import FakeFlag, FakeS3Event
from tests.activity.classes_mock import FakeSQSConn, FakeSQSMessage, FakeSQSQueue
from testfixtures import TempDirectory


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.worker = QueueWorker(settings_mock, self.logger)
        # override the sleep value for faster testing
        self.worker.sleep_seconds = 1

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_load_rules(self):
        "test loading rules YAML file"
        rules = self.worker.load_rules()
        self.assertIsNotNone(rules)

    def test_get_starter_name(self):
        "test rules matching to the S3 notification info"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.queue_worker_article_zip_data)
        expected_starter_name = 'InitialArticleZip'
        starter_name = self.worker.get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)

    def test_get_starter_name_ingest_digest(self):
        "test S3 notification info matching for the ingest digest workflow"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.ingest_digest_data)
        expected_starter_name = 'IngestDigest'
        starter_name = self.worker.get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)

    @patch('queue_worker.Message')
    @patch('tests.activity.classes_mock.FakeSQSQueue.read')
    @patch('queue_worker.QueueWorker.queues')
    @patch('queue_worker.QueueWorker.connect')
    def test_work(self, mock_sqs_connect, mock_queues, mock_queue_read, mock_sqs_message):
        "test the main method of the class"
        directory = TempDirectory()
        mock_sqs_connect = FakeSQSConn(directory)
        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        # create an S3 event message
        s3_event = FakeS3Event()
        mock_queue_read.return_value = s3_event
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        return_value = self.worker.work(flag)
        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(unicode_decode(directory.read("fake_sqs_body")))
        self.assertEqual(out_queue_message, test_data.queue_worker_starter_message)
        self.assertEqual(return_value, None)

    @patch('queue_worker.Message')
    @patch('tests.activity.classes_mock.FakeSQSQueue.read')
    @patch('queue_worker.QueueWorker.queues')
    @patch('queue_worker.QueueWorker.connect')
    def test_work_unknown_bucket(self, mock_sqs_connect, mock_queues, mock_queue_read, mock_sqs_message):
        "test work method with an unrecognised bucket name"
        directory = TempDirectory()
        mock_sqs_connect = FakeSQSConn(directory)
        mock_queues.return_value = FakeSQSQueue(directory), FakeSQSQueue(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        # create an S3 event message
        s3_event = FakeS3Event()
        # here override the bucket name
        s3_event._bucket_name = 'not_a_real_bucket'
        mock_queue_read.return_value = s3_event
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        return_value = self.worker.work(flag)
        # assertion, should be no message in the sqs queue
        out_queue_list = directory.listdir()
        self.assertIsNone(out_queue_list, None)
        self.assertEqual(return_value, None)

if __name__ == '__main__':
    unittest.main()
