import unittest
from mock import patch, MagicMock
from activity.activity_VersionLookup import activity_VersionLookup
import settings_mock
import test_activity_data as testdata
from classes_mock import FakeSession
import provider.lax_provider
from requests.exceptions import ConnectionError

def data(lookup_function, file_name_to_change=None):
    data = testdata.raw_data_activity
    data["version_lookup_function"] = lookup_function
    if file_name_to_change is not None:
        data["file_name"] = file_name_to_change
    return data

def fake_execute_function(arg1, arg2, arg3):
    return "1"

class TestVersionLookup(unittest.TestCase):

    def setUp(self):
        self.versionlookup = activity_VersionLookup(settings_mock, None, None, None, None)
        self.versionlookup.logger = MagicMock()
        self.versionlookup.set_monitor_property = MagicMock()

    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_silent_corrections(self, fake_lookup_functions, fake_session):
        fake_session.return_value = FakeSession({})
        fake_lookup_functions.return_value = "1"
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(data("article_highest_version", "elife-00353-vor-r1.zip"))

        fake_lookup_functions.assert_called_with(provider.lax_provider.article_highest_version, '00353', settings_mock)
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_silent_corrections_version_in_zip(self, fake_lookup_functions, fake_session):
        fake_session.return_value = FakeSession({})
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(data("article_next_version", "elife-00353-vor-v1.zip"))

        fake_lookup_functions.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_normal_process_version_not_in_zip(self, fake_lookup_functions, fake_session):
        fake_session.return_value = FakeSession({})
        fake_lookup_functions.return_value = "1"
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(data("article_next_version", "elife-00353-vor-r1.zip"))

        fake_lookup_functions.assert_called_with(provider.lax_provider.article_next_version, '00353', settings_mock)
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_normal_process(self, fake_lookup_functions, fake_session):
        fake_session.return_value = FakeSession({})
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(data("article_next_version", "elife-00353-vor-v1-20121213000000.zip"))

        fake_lookup_functions.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'emit_monitor_event')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_error(self, fake_execute_function, fake_emit_monitor, fake_session):
        self.versionlookup.logger = MagicMock()
        fake_execute_function.side_effect = Exception("Time out.")
        test_data = data("article_next_version", "elife-00353-vor-r1.zip")

        result = self.versionlookup.do_activity(test_data)

        fake_emit_monitor.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_PERMANENT_FAILURE, result)


    @patch('activity.activity_VersionLookup.Session')
    @patch.object(activity_VersionLookup, 'emit_monitor_event')
    @patch.object(activity_VersionLookup, 'execute_function')
    def test_get_version_error(self, fake_execute_function, fake_emit_monitor, fake_session):
        self.versionlookup.logger = MagicMock()
        fake_execute_function.side_effect = ConnectionError("Protocol Error message.")
        test_data = data("article_next_version", "elife-00353-vor-r1.zip")

        result = self.versionlookup.do_activity(test_data)

        fake_emit_monitor.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == '__main__':
    unittest.main()

