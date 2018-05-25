import unittest
from activity.activity_InvalidateCdn import activity_InvalidateCdn
import settings_mock
from classes_mock import FakeLogger
from mock import patch, call

activity_data = {
                    "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
                    "article_id": "00353",
                    "version": "1"
                }

class TestInvalidateCdn(unittest.TestCase):

    def setUp(self):
        self.invalidatecdn = activity_InvalidateCdn(settings_mock, None, None, None, None)
        self.invalidatecdn.logger = FakeLogger()

    @patch('provider.fastly_provider.purge')
    @patch.object(activity_InvalidateCdn, 'emit_monitor_event')
    def test_invalidation_success(self, fake_emit, purge_mock):
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_SUCCESS)

    @patch('provider.fastly_provider.purge')
    @patch.object(activity_InvalidateCdn, 'emit_monitor_event')
    def test_invalidation_permanent_failure_fastly(self, fake_emit, purge_mock):
        purge_mock.side_effect = Exception("An error occurred calling the Fastly API")
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_PERMANENT_FAILURE)

if __name__ == '__main__':
    unittest.main()
