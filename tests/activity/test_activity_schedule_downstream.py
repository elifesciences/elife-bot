import unittest
from mock import mock, patch
from testfixtures import TempDirectory
import activity.activity_ScheduleDownstream as activity_module
from activity.activity_ScheduleDownstream import (
    activity_ScheduleDownstream as activity_object,
)
from provider import downstream, lax_provider
import tests.activity.settings_mock as settings_mock
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


class TestChooseOutboxes(unittest.TestCase):
    def setUp(self):
        self.rules = downstream.load_config(settings_mock)

    def test_empty_rules(self):
        rules = None
        outbox_list = activity_module.choose_outboxes("vor", True, rules)
        self.assertEqual(outbox_list, [])

    def test_empty_workflow_rules(self):
        rules = {"HEFCE": {}}
        outbox_list = activity_module.choose_outboxes("vor", True, rules)
        self.assertEqual(outbox_list, [])

    def test_choose_outboxes_poa_first(self):
        "first poa version"
        outbox_list = activity_module.choose_outboxes("poa", True, self.rules)
        # schedule the following
        for folder_name in [
            "ovid",
            "publication_email",
            "pubmed",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

        # do not schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "crossref",
            "gooa",
            "oaswitchboard",
            "pmc",
            "pub_router",
            "wos",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_poa_not_first(self):
        "poa but not the first poa"
        outbox_list = activity_module.choose_outboxes("poa", False, self.rules)
        # schedule the following
        for folder_name in [
            "ovid",
            "pubmed",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnpiec",
            "cnki",
            "crossref",
            "gooa",
            "oaswitchboard",
            "pmc",
            "pub_router",
            "publication_email",
            "wos",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_first(self):
        "first vor version"
        outbox_list = activity_module.choose_outboxes("vor", True, self.rules)
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "oaswitchboard",
            "ovid",
            "pmc",
            "pub_router",
            "publication_email",
            "pubmed",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_not_first(self):
        "vor but not the first vor"
        outbox_list = activity_module.choose_outboxes("vor", False, self.rules)
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "pubmed",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_silent_first(self):
        outbox_list = activity_module.choose_outboxes(
            "vor", True, self.rules, "silent-correction"
        )
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
            "pubmed",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_silent_not_first(self):
        "silent correction vor but not the first vor"
        outbox_list = activity_module.choose_outboxes(
            "vor", False, self.rules, "silent-correction"
        )
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
            "pubmed",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )


if __name__ == "__main__":
    unittest.main()
