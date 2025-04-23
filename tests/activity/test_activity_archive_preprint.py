import os
import unittest
import datetime
import zipfile
from mock import patch
from testfixtures import TempDirectory
from provider import utils
import activity.activity_ArchivePreprint as activity_module
from activity.activity_ArchivePreprint import (
    activity_ArchivePreprint as activity_object,
)
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


def outbox_files(folder):
    "count the files in the folder ignoring .gitkeep or files starting with ."
    return [
        file_name for file_name in os.listdir(folder) if not file_name.startswith(".")
    ]


def outbox_zip_file(folder_name):
    "zip file path in the destination folder"
    file_list = outbox_files(folder_name)
    if not file_list:
        return None
    zip_file_path = os.path.join(folder_name, file_list[0])
    return zip_file_path


class TestArchivePreprint(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def zip_assertions(self, zip_file_path, expected_zip_file_name, expected_zip_files):
        zip_file_name = None
        if zip_file_path:
            zip_file_name = zip_file_path.split(os.sep)[-1]
        self.assertEqual(zip_file_name, expected_zip_file_name)
        if zip_file_path:
            with zipfile.ZipFile(zip_file_path) as open_zip:
                self.assertEqual(
                    sorted(open_zip.namelist()), sorted(expected_zip_files)
                )
        else:
            self.assertEqual(None, expected_zip_files)

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self, fake_session, fake_storage_context, fake_get_current_datetime
    ):
        directory = TempDirectory()
        fake_session.return_value = FakeSession(
            activity_test_data.post_preprint_publication_session_example()
        )
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            "2025-04-22 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
        test_destination_folder = directory.path
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )

        expected_file_count = 1
        expected_zip_file_name = "elife-95901-rp-v2-20250422000000.zip"
        expected_zip_files = [
            "content/",
            "content/24301711.pdf",
            "content/24301711.xml",
            "content/24301711v1_fig1.tif",
            "content/24301711v1_tbl1.tif",
            "content/24301711v1_tbl1a.tif",
            "content/24301711v1_tbl2.tif",
            "content/24301711v1_tbl3.tif",
            "content/24301711v1_tbl4.tif",
            "directives.xml",
            "manifest.xml",
            "mimetype",
            "transfer.xml",
        ]

        # invoke
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # assert
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            len(outbox_files(test_destination_folder)), expected_file_count
        )
        self.assertTrue(
            (
                "ArchivePreprint, 10.7554/eLife.95901.2 copying"
                " from s3://prod-elife-epp-meca/95901-v1-meca.zip"
                " to s3://archive_bucket/elife-95901-rp-v2-20250422000000.zip"
            )
            in self.activity.logger.loginfo
        )
        # should be one zip file
        zip_file_path = outbox_zip_file(test_destination_folder)
        self.zip_assertions(zip_file_path, expected_zip_file_name, expected_zip_files)

    @patch.object(FakeStorageContext, "copy_resource")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_copy_failure(
        self,
        fake_session,
        fake_storage_context,
        fake_get_current_datetime,
        fake_copy_resource,
    ):
        "test failure to copy a bucket object"
        directory = TempDirectory()
        fake_session.return_value = FakeSession(
            activity_test_data.post_preprint_publication_session_example()
        )
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            "2025-04-22 00:00:00", "%Y-%m-%d %H:%M:%S"
        )
        test_destination_folder = directory.path
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_copy_resource.side_effect = Exception("An exception")

        expected_file_count = 0
        expected_zip_file_name = None
        expected_zip_files = None

        # invoke
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # assert
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(
            len(outbox_files(test_destination_folder)), expected_file_count
        )
        # should be no zip file
        zip_file_path = outbox_zip_file(test_destination_folder)
        self.zip_assertions(zip_file_path, expected_zip_file_name, expected_zip_files)
