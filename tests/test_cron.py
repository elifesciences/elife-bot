import unittest
import time
from ddt import ddt, data
from mock import patch
import tests.settings_mock as settings_mock
import cron


@ddt
class TestCron(unittest.TestCase):
    def setUp(self):
        pass

    @patch.object(time, 'gmtime')
    @patch.object(cron, 'workflow_conditional_start')
    @data(
        "1970-01-01 11:45:00",
        "1970-01-01 17:45:00",
        "1970-01-01 12:30:00",
        "1970-01-01 20:30:00",
        "1970-01-01 21:30:00",
        "1970-01-01 21:45:00",
        "1970-01-01 22:30:00",
        "1970-01-01 22:45:00",
        "1970-01-01 23:00:00",
        "1970-01-01 23:30:00",
        "1970-01-01 23:45:00",
    )
    def test_run_cron(self, date_time, fake_workflow_start, fake_gmtime):
        fake_gmtime.return_value = time.strptime(date_time, '%Y-%m-%d %H:%M:%S')
        self.assertIsNone(cron.run_cron(settings_mock))


if __name__ == '__main__':
    unittest.main()
