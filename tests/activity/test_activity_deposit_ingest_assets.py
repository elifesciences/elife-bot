import unittest
from mock import patch
from activity.activity_DepositIngestAssets import activity_DepositIngestAssets
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeStorageContext, FakeSession, FakeLogger
import tests.activity.test_activity_data as test_activity_data


ACTIVITY_DATA = {
    "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
    "article_id": "00353",
    "result": "ingested",
    "status": "vor",
    "version": "1",
    "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
    "requested_action": "ingest",
    "message": None,
    "update_date": "2012-12-13T00:00:00Z"
    }

class TestDepositIngestAssets(unittest.TestCase):
    def setUp(self):
        self.activity = activity_DepositIngestAssets(settings_mock, FakeLogger(), None, None, None)

    @patch('activity.activity_DepositIngestAssets.get_session')
    @patch('activity.activity_DepositIngestAssets.storage_context')
    @patch.object(activity_DepositIngestAssets, 'emit_monitor_event')
    def test_activity_success(self, fake_emit, fake_storage_context, fake_session):

        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)

        result = self.activity.do_activity(ACTIVITY_DATA)

        self.assertEqual(self.activity.ACTIVITY_SUCCESS, result)

    @patch('activity.activity_DepositIngestAssets.get_session')
    @patch('activity.activity_DepositIngestAssets.storage_context')
    @patch.object(activity_DepositIngestAssets, 'emit_monitor_event')
    def test_activity_permanent_failure(self, fake_emit, fake_storage_context, fake_session):

        fake_storage_context.side_effect = Exception("An error occurred")
        fake_session.return_value = FakeSession(test_activity_data.session_example)

        result = self.activity.do_activity(ACTIVITY_DATA)

        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == '__main__':
    unittest.main()
