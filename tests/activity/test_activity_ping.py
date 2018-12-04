import unittest
from activity.activity_PingWorker import activity_PingWorker
from tests.activity.classes_mock import FakeLogger
import tests.activity.settings_mock as settings_mock


class TestPingWorker(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PingWorker(settings_mock, fake_logger, None, None, None)

    def test_do_activity(self):
        expected_result = True
        result = self.activity.do_activity()
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
