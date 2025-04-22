import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import utils
import activity.activity_CleanOutbox as activity_module
from activity.activity_CleanOutbox import activity_CleanOutbox as activity_class
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestCleanOutbox(unittest.TestCase):
    def setUp(self):
        self.activity = activity_class(settings_mock, FakeLogger(), None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch("provider.outbox_provider.storage_context")
    @patch.object(utils, "set_datestamp")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_set_datestamp,
        fake_outbox_storage_context,
    ):
        directory = TempDirectory()
        fake_session.return_value = FakeSession(SESSION_DICT)
        fake_set_datestamp.return_value = "20250417"
        # populate the outbox folder
        outbox_file_name = "finish_preprint/outbox/elife-preprint-95901-v1.xml"
        outbox_file_path = os.path.join(directory.path, outbox_file_name)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(outbox_file_path), exist_ok=True)
        # write test file
        with open(outbox_file_path, "w", encoding="utf-8") as open_file:
            open_file.write("test")
        resources = [outbox_file_name]

        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        expected_result = activity_class.ACTIVITY_SUCCESS
        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertTrue(
            (
                "CleanOutbox, version DOI 10.7554/eLife.95901.1 published_file_names:"
                " ['finish_preprint/outbox/elife-preprint-95901-v1.xml']"
            )
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "CleanOutbox, version DOI 10.7554/eLife.95901.1 approved_file_names:"
                " ['finish_preprint/outbox/elife-preprint-95901-v1.xml']"
            )
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            "CleanOutbox, moving files from outbox folder to published folder"
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "CleanOutbox, version DOI 10.7554/eLife.95901.1 to_folder:"
                " finish_preprint/published/20250417/"
            )
            in self.activity.logger.loginfo
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": True, "clean_status": True, "activity_status": True},
        )

    @patch("provider.outbox_provider.storage_context")
    @patch.object(utils, "set_datestamp")
    @patch.object(activity_module, "get_session")
    def test_do_activity_empty_outbox(
        self,
        fake_session,
        fake_set_datestamp,
        fake_outbox_storage_context,
    ):
        "test if no XML is found in the outbox folder"
        directory = TempDirectory()

        fake_session.return_value = FakeSession(SESSION_DICT)
        fake_set_datestamp.return_value = "20250417"
        resources = []
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        expected_result = activity_class.ACTIVITY_SUCCESS
        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertTrue(
            (
                "CleanOutbox, version DOI 10.7554/eLife.95901.1,"
                " no published files found in the outbox"
            )
            in self.activity.logger.loginfo
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": True, "clean_status": None, "activity_status": None},
        )

    @patch("provider.outbox_provider.outbox_folder")
    @patch.object(activity_module, "get_session")
    def test_do_activity_no_outbox_folder(
        self,
        fake_session,
        fake_outbox_folder,
    ):
        "test if the outbox folder is not found"
        fake_outbox_folder.return_value = None
        fake_session.return_value = FakeSession(SESSION_DICT)
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertEqual(
            (
                "CleanOutbox, version DOI 10.7554/eLife.95901.1 outbox_folder None,"
                " published_folder finish_preprint/published/, failing the workflow"
            ),
            self.activity.logger.logerror,
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": None, "clean_status": None, "activity_status": None},
        )
