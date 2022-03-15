import unittest
import copy
from ddt import ddt, data, unpack
from mock import patch
import activity.activity_ScheduleCrossref as activity_module
from activity.activity_ScheduleCrossref import activity_ScheduleCrossref
from provider import lax_provider
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock
import tests.activity.test_activity_data as testdata


@ddt
class TestScheduleCrossref(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_ScheduleCrossref(
            settings_mock, fake_logger, None, None, None
        )

    def tearDown(self):
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_ScheduleCrossref.get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_ScheduleCrossref, "emit_monitor_event")
    @patch.object(activity_ScheduleCrossref, "set_monitor_property")
    @data(
        ("elife-00353-v1.xml", True),
        (None, False),
    )
    @unpack
    def test_do_activity(
        self,
        xml_filename,
        expected_result,
        mock_set_monitor_property,
        mock_emit_monitor_event,
        fake_storage_context,
        fake_session_mock,
        fake_get_xml_file_name,
    ):
        mock_emit_monitor_event.return_value = True
        mock_set_monitor_property.return_value = True
        fake_session_mock.return_value = FakeSession(testdata.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = None
        if xml_filename:
            fake_get_xml_file_name.return_value = xml_filename
        result = self.activity.do_activity(testdata.ExpandArticle_data)
        self.assertEqual(result, expected_result)

    @patch.object(lax_provider, "article_highest_version")
    @patch("activity.activity_ScheduleCrossref.get_session")
    def test_do_activity_silent_correction(
        self, fake_session_mock, fake_highest_version
    ):
        expected_result = True
        session_dict = copy.copy(testdata.session_example)
        session_dict["run_type"] = "silent-correction"
        fake_session_mock.return_value = FakeSession(session_dict)
        fake_highest_version.return_value = 2
        result = self.activity.do_activity(testdata.ExpandArticle_data)
        self.assertEqual(result, expected_result)
