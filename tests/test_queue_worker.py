import unittest
import time
import json
from mock import Mock, patch
import settings_mock
from queue_worker import QueueWorker
from S3utility.s3_notification_info import S3NotificationInfo
import tests.test_data as test_data
from tests.activity.classes_mock import FakeSQSConn, FakeSQSMessage, FakeSQSQueue
from testfixtures import TempDirectory

class FakeFlag():
    "a fake object to return process monitoring status"
    def __init__(self, timeout_seconds=1):
        self.timeout_seconds = timeout_seconds
        self.green_value = True

    def green(self):
        "first return True, wait, then return False"
        return_value = self.green_value
        self.green_value = False
        time.sleep(self.timeout_seconds)
        return return_value

class FakeS3Event():
    "object to test an S3 notification event from an SQS queue"
    def __init__(self):
        self.notification_type = 'S3Event'
        self.id = None
        # test data below
        self._event_name = u'ObjectCreated:Put'
        self._event_time = u'2016-07-28T16:14:27.809576Z'
        self._bucket_name =  u'jen-elife-production-final'
        self._file_name =  u'elife-00353-vor-r1.zip'
        self._file_etag = u'e7f639f63171c097d4761e2d2efe8dc4'
        self._file_size = 1097506
    def event_name(self):
        return self._event_name
    def event_time(self):
        return self._event_time
    def bucket_name(self):
        return self._bucket_name
    def file_name(self):
        return self._file_name
    def file_etag(self):
        return self._file_etag
    def file_size(self):
        return self._file_size


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
        out_queue_message = json.loads(directory.read("fake_sqs_body"))
        self.assertEqual(out_queue_message, test_data.queue_worker_starter_message)


if __name__ == '__main__':
    unittest.main()
