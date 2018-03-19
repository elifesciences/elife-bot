import unittest
from mock import Mock
import settings_mock
from queue_worker import QueueWorker
from S3utility.s3_notification_info import S3NotificationInfo
import tests.test_data as test_data


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.worker = QueueWorker(settings_mock, self.logger)

    def test_get_load_rules(self):
        "test loading rules YAML file"
        rules = self.worker.load_rules()
        print(rules)
        self.assertIsNotNone(rules)

    def test_get_starter_name(self):
        "test rules matching to the S3 notification info"
        rules = test_data.queue_worker_rules
        info = S3NotificationInfo.from_dict(test_data.queue_worker_article_zip_data)
        expected_starter_name = 'InitialArticleZip'
        starter_name = self.worker.get_starter_name(rules, info)
        self.assertEqual(starter_name, expected_starter_name)

if __name__ == '__main__':
    unittest.main()
