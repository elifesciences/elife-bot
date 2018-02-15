import unittest
from mock import patch, ANY

import settings_mock
from activity.activity_AcceptVersionReason import activity_AcceptVersionReason
from classes_mock import FakeSession
from classes_mock import FakeLogger


test_data = {
    'run': '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
    'version_reason': 'version reason text',
    'scheduled_publication_date': '1518688960'
}

session_example = { 'expanded_folder': '7777777701234.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                    'article_id': '7777777701234',
                    'version': '1',
                    'update_date': '2012-12-13T00:00:00Z',
                    'status': 'vor'}


class TestAcceptVersionReason(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.acceptreason = activity_AcceptVersionReason(settings_mock, fake_logger, None, None, None)

    @patch('activity.activity_AcceptVersionReason.get_session')
    @patch.object(activity_AcceptVersionReason, 'set_monitor_property')
    @patch.object(activity_AcceptVersionReason, 'emit_monitor_event')
    def test_ready_to_publish(self, fake_emit_monitor, fake_set_property, fake_session):

        fake_session.return_value = FakeSession(session_example)
        result = self.acceptreason.do_activity(test_data)
        self.assertEqual(result, self.acceptreason.ACTIVITY_SUCCESS)
        fake_set_property.assert_any_call(ANY, '7777777701234', 'version_reason', 'version reason text', 'text',
                                          version='1')
        fake_set_property.assert_any_call(ANY, '7777777701234', 'scheduled_publication_date', '1518688960', 'text',
                                          version='1')


if __name__ == '__main__':
    unittest.main()
