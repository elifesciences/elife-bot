import unittest
from mock import patch, call
from activity.activity_InvalidateCdn import activity_InvalidateCdn
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession
import tests.activity.test_activity_data as test_activity_data


activity_data = {
    "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
    "article_id": "353",
    "version": "1",
}


class TestInvalidateCdn(unittest.TestCase):
    def setUp(self):
        self.invalidatecdn = activity_InvalidateCdn(
            settings_mock, None, None, None, None
        )
        self.invalidatecdn.logger = FakeLogger()

    @patch("activity.activity_InvalidateCdn.get_session")
    @patch("provider.fastly_provider.purge")
    @patch.object(activity_InvalidateCdn, "emit_monitor_event")
    def test_invalidation_success(self, fake_emit, purge_mock, fake_session):
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_SUCCESS)

    @patch("activity.activity_InvalidateCdn.get_session")
    @patch("provider.fastly_provider.purge")
    @patch.object(activity_InvalidateCdn, "emit_monitor_event")
    def test_invalidation_permanent_failure_fastly(
        self, fake_emit, purge_mock, fake_session
    ):
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        purge_mock.side_effect = Exception("An error occurred calling the Fastly API")
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_PERMANENT_FAILURE)


if __name__ == "__main__":
    unittest.main()
