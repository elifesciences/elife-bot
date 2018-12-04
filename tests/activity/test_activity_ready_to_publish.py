import unittest
from mock import patch
import tests.activity.settings_mock as settings_mock
from activity.activity_ReadyToPublish import activity_ReadyToPublish
from tests.activity.classes_mock import FakeSession, FakeLogger

test_data = {
    'run': '1ee54f9a-cb28-4c8e-8232-4b317cf4beda'
}

session_example = { 'expanded_folder': '7777777701234.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                    'article_id': '7777777701234',
                    'version': '1',
                    'update_date': '2012-12-13T00:00:00Z',
                    'status': 'vor'}

class TestReadyToPublish(unittest.TestCase):
    def setUp(self):
        self.readytopublish = activity_ReadyToPublish(settings_mock, FakeLogger(), None, None, None)

    @patch.object(activity_ReadyToPublish, 'set_monitor_property')
    @patch('activity.activity_ReadyToPublish.get_session')
    @patch.object(activity_ReadyToPublish, 'emit_monitor_event')
    def test_ready_to_publish(self, fake_emit_monitor, fake_session, fake_set_monitor_property):
        fake_session.return_value = FakeSession(session_example)
        result = self.readytopublish.do_activity(test_data)
        self.assertEqual(result, self.readytopublish.ACTIVITY_SUCCESS)

    @patch.object(activity_ReadyToPublish, 'prepare_ready_to_publish_message')
    @patch('activity.activity_ReadyToPublish.get_session')
    @patch.object(activity_ReadyToPublish, 'emit_monitor_event')
    def test_ready_to_publish_error(self, fake_emit_monitor, fake_session, fake_prepare):
        fake_session.return_value = FakeSession(session_example)
        fake_prepare.side_effect = Exception("An error occurred")
        result = self.readytopublish.do_activity(test_data)
        self.assertEqual(result, self.readytopublish.ACTIVITY_PERMANENT_FAILURE)

    def test_preview_path(self):
        result = self.readytopublish.preview_path(settings_mock.article_path_pattern, "34427", "1")
        self.assertEqual(result, "/articles/34427v1")


if __name__ == '__main__':
    unittest.main()
