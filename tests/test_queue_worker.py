import unittest
from mock import Mock
import queue_worker


class TestQueueWorker(unittest.TestCase):
    def setUp(self):
        queue_worker.settings = Mock()

    def test_get_starter_name(self):
        "test rules in the new file workflows YAML file"
        rules = queue_worker.load_rules()
        self.assertIsNotNone(rules)


if __name__ == '__main__':
    unittest.main()
