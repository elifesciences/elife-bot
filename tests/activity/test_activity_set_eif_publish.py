import unittest
from activity.activity_SetEIFPublish import activity_SetEIFPublish
import settings_mock
import test_activity_data as test_data
from mock import patch, MagicMock
from classes_mock import FakeSession
from classes_mock import FakeStorageContext
from ddt import ddt, data

@ddt
class tests_SetEIFPublish(unittest.TestCase):

    def setUp(self):
        self.seteifpublish = activity_SetEIFPublish(settings_mock, None, None, None, None)

    @patch.object(activity_SetEIFPublish, 'emit_monitor_event')
    @patch('activity.activity_SetEIFPublish.storage_context')
    @patch.object(activity_SetEIFPublish, 'get_eif')
    @patch('activity.activity_SetEIFPublish.get_session')
    @data(test_data.data_example_before_publish)
    def test_do_activity(self, data, fake_session, fake_get_eif, fake_storage_context, fake_emit_monitor_event):
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_get_eif.return_value = test_data.json_output_parameter_example
        fake_storage_context.return_value = FakeStorageContext()

        self.seteifpublish.logger = MagicMock()

        result = self.seteifpublish.do_activity(data)

        fake_emit_monitor_event.assert_called_with(settings_mock, data['article_id'], data['version'],
                                                   data['run'], self.seteifpublish.pretty_name, "end",
                                                   "Finished to set EIF to publish")
        self.assertEqual(result, self.seteifpublish.ACTIVITY_SUCCESS)

    @patch.object(activity_SetEIFPublish, 'emit_monitor_event')
    @patch.object(activity_SetEIFPublish, 'get_eif')
    @patch('activity.activity_SetEIFPublish.get_session')
    @data(test_data.data_example_before_publish)
    def test_error_fetch_eif(self, data, fake_session, fake_get_eif, fake_emit_monitor_event):
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_get_eif.side_effect = Exception('Value error')
        self.seteifpublish.logger = MagicMock()

        result = self.seteifpublish.do_activity(data)

        fake_emit_monitor_event.assert_called_with(settings_mock, data['article_id'], data['version'],
                                                   data['run'], self.seteifpublish.pretty_name, "error",
                                                   "Could not fetch/load EIF data. Error details: Value error")
        self.assertEqual(result, self.seteifpublish.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_SetEIFPublish, 'emit_monitor_event')
    @patch('activity.activity_SetEIFPublish.storage_context')
    @patch.object(activity_SetEIFPublish, 'get_eif')
    @patch('activity.activity_SetEIFPublish.get_session')
    @data(test_data.data_example_before_publish)
    def test_error_update_eif(self, data, fake_session, fake_get_eif, fake_storage_context, fake_emit_monitor_event):
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_get_eif.return_value = None
        fake_storage_context.return_value = FakeStorageContext()

        self.seteifpublish.logger = MagicMock()

        result = self.seteifpublish.do_activity(data)

        fake_emit_monitor_event.assert_called_with(settings_mock, data['article_id'], data['version'],
                                                   data['run'], self.seteifpublish.pretty_name, "error",
                                                   "There is something wrong with EIF data and/or we could not upload "
                                                   "it. Error details: 'NoneType' object does not support item "
                                                   "assignment")
        self.assertEqual(result, self.seteifpublish.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_SetEIFPublish, 'emit_monitor_event')
    @patch('activity.activity_SetEIFPublish.get_session')
    @data(test_data.data_example_before_publish)
    def test_error_no_eif_location(self, data, fake_session, fake_emit_monitor_event):
        fake_session.return_value = FakeSession({})

        self.seteifpublish.logger = MagicMock()

        result = self.seteifpublish.do_activity(data)

        fake_emit_monitor_event.assert_called_with(settings_mock, data['article_id'], data['version'],
                                                   data['run'], self.seteifpublish.pretty_name, "error",
                                                   "eif_location not available")
        self.assertEqual(result, self.seteifpublish.ACTIVITY_PERMANENT_FAILURE)


if __name__ == '__main__':
    unittest.main()
