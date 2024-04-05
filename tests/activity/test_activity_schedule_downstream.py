import unittest
from mock import mock, patch
from testfixtures import TempDirectory
import activity.activity_ScheduleDownstream as activity_module
from activity.activity_ScheduleDownstream import (
    activity_ScheduleDownstream as activity_object,
)
from provider import lax_provider
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


class TestScheduleDownstream(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("provider.lax_provider.article_first_by_status")
    @patch.object(lax_provider, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self, fake_activity_storage_context, fake_storage_context, fake_first
    ):
        directory = TempDirectory()
        expected_result = True
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_activity_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_first.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(lax_provider, "get_xml_file_name")
    @patch.object(lax_provider, "article_first_by_status")
    def test_do_activity_exception(self, fake_first, fake_get_xml_file_name):
        expected_result = False
        fake_get_xml_file_name.side_effect = Exception("Something went wrong!")
        fake_first.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # check assertions
        self.assertEqual(result, expected_result)
