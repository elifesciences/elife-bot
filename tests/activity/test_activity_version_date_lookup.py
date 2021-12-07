import unittest
from mock import patch, MagicMock
from activity.activity_VersionDateLookup import activity_VersionDateLookup
from tests.activity.classes_mock import FakeSession
import tests.activity.settings_mock as settings_mock
import tests.activity.test_activity_data as testdata


class TestVersionDateLookup(unittest.TestCase):
    def setUp(self):
        self.versiondatelookup = activity_VersionDateLookup(
            settings_mock, None, None, None, None
        )

    @patch("activity.activity_VersionDateLookup.get_session")
    @patch("provider.lax_provider.article_version_date_by_version")
    def test_get_version_date_silent_corrections(
        self, fake_date_lookup_function, fake_session
    ):
        fake_session_obj = FakeSession(testdata.data_example_before_publish)
        fake_session.return_value = fake_session_obj
        fake_date_lookup_function.return_value = "2015-11-30T00:00:00Z"
        self.versiondatelookup.emit_monitor_event = MagicMock()

        result = self.versiondatelookup.do_activity(testdata.raw_data_activity)

        fake_date_lookup_function.assert_called_with("00353", "1", settings_mock)
        self.assertEqual(self.versiondatelookup.ACTIVITY_SUCCESS, result)
        self.assertEqual(
            fake_session_obj.session_dict["update_date"], "2015-11-30T00:00:00Z"
        )

    @patch("activity.activity_VersionDateLookup.get_session")
    @patch("provider.lax_provider.article_version_date_by_version")
    def test_get_version_silent_corrections_version_date_in_zip(
        self, fake_lookup_functions, fake_session
    ):
        data_rep = testdata.data_example_before_publish.copy()
        data_rep["filename_last_element"] = "elife-00353-vor-v1-20121213000000.zip"
        fake_session_obj = FakeSession(data_rep)
        fake_session.return_value = fake_session_obj
        self.versiondatelookup.emit_monitor_event = MagicMock()

        result = self.versiondatelookup.do_activity(testdata.raw_data_activity)

        fake_lookup_functions.assert_not_called()
        self.assertEqual(self.versiondatelookup.ACTIVITY_SUCCESS, result)
        self.assertEqual(
            fake_session_obj.session_dict["update_date"], "2012-12-13T00:00:00Z"
        )

    @patch("activity.activity_VersionDateLookup.get_session")
    @patch("provider.lax_provider.article_version_date_by_version")
    def test_get_version_date_silent_corrections_error(
        self, fake_date_lookup_function, fake_session
    ):
        fake_session_obj = FakeSession(testdata.data_example_before_publish)
        fake_session.return_value = fake_session_obj
        fake_date_lookup_function.side_effect = Exception(
            "Error in article_publication_date_by_version: "
            "Version date not found. Status: 500"
        )
        self.versiondatelookup.emit_monitor_event = MagicMock()
        self.versiondatelookup.logger = MagicMock()

        result = self.versiondatelookup.do_activity(testdata.raw_data_activity)

        fake_date_lookup_function.assert_called_with("00353", "1", settings_mock)
        self.assertRaises(Exception, fake_date_lookup_function)
        self.assertEqual(self.versiondatelookup.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == "__main__":
    unittest.main()
