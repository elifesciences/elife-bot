import unittest
from mock import patch, MagicMock
from requests.exceptions import ConnectionError
from activity.activity_VersionLookup import activity_VersionLookup
import provider.lax_provider
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeSession
import tests.activity.test_activity_data as testdata


def data(lookup_function, file_name_to_change=None, run_type=None):
    data = testdata.raw_data_activity
    data["version_lookup_function"] = lookup_function
    data["run_type"] = run_type
    if file_name_to_change is not None:
        data["file_name"] = file_name_to_change
    return data


def fake_execute_function():
    return "1"


class TestVersionLookup(unittest.TestCase):
    def setUp(self):
        self.versionlookup = activity_VersionLookup(
            settings_mock, None, None, None, None
        )
        self.versionlookup.logger = MagicMock()
        self.versionlookup.set_monitor_property = MagicMock()

    @patch("activity.activity_VersionLookup.get_session")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_silent_corrections(self, fake_lookup_functions, fake_session):
        run_type = "silent-correction"
        named_session = FakeSession({})
        fake_session.return_value = named_session
        fake_lookup_functions.return_value = "1"
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(
            data("article_highest_version", "elife-00353-vor-r1.zip", run_type)
        )

        fake_lookup_functions.assert_called_with(
            provider.lax_provider.article_highest_version, "00353", settings_mock
        )
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)
        # test the session for run_type
        self.assertEqual(named_session.get_value("run_type"), run_type)

    @patch("activity.activity_VersionLookup.get_session")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_silent_corrections_version_in_zip(
        self, fake_lookup_functions, fake_session
    ):
        named_session = FakeSession({})
        fake_session.return_value = named_session
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(
            data("article_next_version", "elife-00353-vor-v1.zip")
        )

        fake_lookup_functions.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)
        # test the session for run_type
        self.assertEqual(named_session.get_value("run_type"), None)

    @patch("activity.activity_VersionLookup.get_session")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_normal_process_version_not_in_zip(
        self, fake_lookup_functions, fake_session
    ):
        fake_session.return_value = FakeSession({})
        fake_lookup_functions.return_value = "1"
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(
            data("article_next_version", "elife-00353-vor-r1.zip")
        )

        fake_lookup_functions.assert_called_with(
            provider.lax_provider.article_next_version, "00353", settings_mock
        )
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch("activity.activity_VersionLookup.get_session")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_normal_process(self, fake_lookup_functions, fake_session):
        fake_session.return_value = FakeSession({})
        self.versionlookup.emit_monitor_event = MagicMock()

        result = self.versionlookup.do_activity(
            data("article_next_version", "elife-00353-vor-v1-20121213000000.zip")
        )

        fake_lookup_functions.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_SUCCESS, result)

    @patch("activity.activity_VersionLookup.get_session")
    @patch.object(activity_VersionLookup, "emit_monitor_event")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_error_timeout(
        self, fake_execute_function, fake_emit_monitor, fake_session
    ):
        fake_session.return_value = FakeSession({})
        self.versionlookup.logger = MagicMock()
        fake_execute_function.side_effect = Exception("Time out.")
        test_data = data("article_next_version", "elife-00353-vor-r1.zip")

        result = self.versionlookup.do_activity(test_data)

        fake_emit_monitor.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_PERMANENT_FAILURE, result)

    @patch("activity.activity_VersionLookup.get_session")
    @patch.object(activity_VersionLookup, "emit_monitor_event")
    @patch("activity.activity_VersionLookup.execute_function")
    def test_get_version_error_protocol_error_message(
        self, fake_execute_function, fake_emit_monitor, fake_session
    ):
        fake_session.return_value = FakeSession({})
        self.versionlookup.logger = MagicMock()
        fake_execute_function.side_effect = ConnectionError("Protocol Error message.")
        test_data = data("article_next_version", "elife-00353-vor-r1.zip")

        result = self.versionlookup.do_activity(test_data)

        fake_emit_monitor.assert_not_called()
        self.assertEqual(self.versionlookup.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == "__main__":
    unittest.main()
