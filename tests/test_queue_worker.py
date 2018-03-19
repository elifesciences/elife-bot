import unittest
from mock import Mock
import settings_mock
from queue_worker import QueueWorker


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.worker = QueueWorker(settings_mock, self.logger)

    def test_get_starter_name(self):
        "test rules in the new file workflows YAML file"
        rules = self.worker.load_rules()
        self.assertIsNotNone(rules)


if __name__ == '__main__':
    unittest.main()
