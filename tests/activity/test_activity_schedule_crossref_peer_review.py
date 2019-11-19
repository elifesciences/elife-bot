import unittest
from mock import mock, patch
import activity.activity_ScheduleCrossrefPeerReview as activity_module
from activity.activity_ScheduleCrossrefPeerReview import (
    activity_ScheduleCrossrefPeerReview as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


class TestScheduleCrossrefPeerReview(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch('provider.lax_provider.article_first_by_status')
    @patch('provider.article.storage_context')
    @patch.object(activity_module, 'storage_context')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_object, 'xml_sub_article_exists')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch.object(activity_object, 'set_monitor_property')
    def test_do_activity(self, fake_set_property, fake_emit_monitor,
                         fake_sub_article_exists, fake_session_mock,
                         fake_storage_context, fake_article_storage_context, fake_first):
        expected_result = True
        fake_session_mock.return_value = FakeSession(activity_test_data.session_example)
        fake_set_property.return_value = True
        fake_emit_monitor.return_value = True
        fake_storage_context.return_value = FakeStorageContext()
        fake_article_storage_context.return_value = FakeStorageContext()
        fake_first.return_value = True
        fake_sub_article_exists.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        # check assertions
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
