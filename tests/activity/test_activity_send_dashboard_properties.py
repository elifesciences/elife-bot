import unittest
from mock import patch, ANY
from testfixtures import TempDirectory
from activity import activity_SendDashboardProperties as activity_module
from activity.activity_SendDashboardProperties import activity_SendDashboardProperties
from tests.activity import helpers, settings_mock
from tests.activity.classes_mock import (
    FakeSession,
    FakeStorageContext,
    FakeLogger,
)
import tests.activity.test_activity_data as test_data


class TestSendDashboardEvents(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.send_dashboard_properties = activity_SendDashboardProperties(
            settings_mock, fake_logger, None, None, None
        )
        self.directory = TempDirectory()

    def tearDown(self):
        self.directory.cleanup()
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder(
            test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("provider.lax_provider.get_xml_file_name")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_SendDashboardProperties, "emit_monitor_event")
    @patch.object(activity_SendDashboardProperties, "set_monitor_property")
    def test_do_activity(
        self,
        fake_set_monitor_property,
        fake_emit_monitor_event,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
    ):

        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = "elife-00353-v1.xml"
        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

        self.assertEqual(result, True)

        fake_set_monitor_property.assert_any_call(
            ANY, "353", "doi", "10.7554/eLife.00353", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "title", "A good life", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "status", "VOR", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "publication-date", "2012-12-13", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "article-type", "discussion", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "corresponding-authors", "Eve Marder", "text", version="1"
        )
        fake_set_monitor_property.assert_any_call(
            ANY, "353", "authors", "Eve Marder", "text", version="1"
        )

        fake_emit_monitor_event.assert_any_call(
            ANY,
            "353",
            "1",
            "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
            "Send dashboard properties",
            "start",
            "Starting send of article properties to dashboard for article 353",
        )
        fake_emit_monitor_event.assert_any_call(
            ANY,
            "353",
            "1",
            "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
            "Send dashboard properties",
            "end",
            "Article properties sent to dashboard for article  353",
        )

    @patch("provider.lax_provider.get_xml_file_name")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_SendDashboardProperties, "emit_monitor_event")
    @patch.object(activity_SendDashboardProperties, "set_monitor_property")
    def test_do_activity_failure_no_xml(
        self,
        fake_set_monitor_property,
        fake_emit_monitor_event,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
    ):
        "test if no XML file is supplied, will fail"
        fake_set_monitor_property.return_value = True
        fake_emit_monitor_event.return_value = True
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = None

        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

        self.assertEqual(
            result, self.send_dashboard_properties.ACTIVITY_PERMANENT_FAILURE
        )

    @patch("provider.lax_provider.get_xml_file_name")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_SendDashboardProperties, "emit_monitor_event")
    @patch.object(activity_SendDashboardProperties, "set_monitor_property")
    def test_do_activity_failure_invalid_xml(
        self,
        fake_set_monitor_property,
        fake_emit_monitor_event,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
    ):
        "test if XML fails to parse, here an incorrect pub_date, will fail"
        fake_set_monitor_property.return_value = True
        fake_emit_monitor_event.return_value = True
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext(
            "tests/files_source", ["elife-00353-v1_bad_pub_date.xml"]
        )
        fake_get_xml_file_name.return_value = "elife-00353-v1_bad_pub_date.xml"

        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

        self.assertEqual(
            result, self.send_dashboard_properties.ACTIVITY_PERMANENT_FAILURE
        )
