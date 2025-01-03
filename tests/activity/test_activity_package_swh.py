import os
import zipfile
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import software_heritage
import activity.activity_PackageSWH as activity_module
from activity.activity_PackageSWH import activity_PackageSWH as activity_object
from tests.activity import helpers, settings_mock
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeStorageContext,
    FakeSession,
)
import tests.activity.test_activity_data as testdata


class TestPackageSWH(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])
        self.activity.clean_tmp_dir()

    @patch("requests.get")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(self, mock_storage_context, mock_session, fake_requests_get):
        directory = TempDirectory()
        expected_zip_file_name = "elife-30274-v1-era.zip"
        expected_zip_file_size = 1161501
        mock_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_response = FakeResponse(200)
        # zip file
        with open(
            "tests/files_source/software_heritage/archive_30274.zip", "rb"
        ) as open_file:
            fake_response.content = open_file.read()
        fake_requests_get.return_value = fake_response

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_SUCCESS)

        # Check destination folder file
        bucket_folder_path = os.path.join(
            directory.path,
            software_heritage.BUCKET_FOLDER,
            testdata.SoftwareHeritageDeposit_data_example.get("run"),
        )
        files = sorted(os.listdir(bucket_folder_path))

        index = 0
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        for file in compare_files:
            self.assertEqual(expected_zip_file_name, file)
            statinfo = os.stat(bucket_folder_path + "/" + file)
            self.assertEqual(
                expected_zip_file_size,
                statinfo.st_size,
            )
            index += 1

    @patch.object(activity_module, "download_file")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_download_file_exception(
        self, mock_storage_context, mock_session, fake_download_file
    ):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_file.side_effect = Exception("Exception in download_file")

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("zipfile.ZipFile")
    @patch.object(activity_module, "download_file")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_zip_file_exception(
        self, mock_storage_context, mock_session, fake_download_file, fake_zipfile
    ):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_file.return_value = True
        fake_zipfile.side_effect = zipfile.BadZipFile("Exception in opening zip file")

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(FakeStorageContext, "set_resource_from_filename")
    @patch("requests.get")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_bucket_exception(
        self, mock_storage_context, mock_session, fake_requests_get, fake_set_resource
    ):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_response = FakeResponse(200)
        # zip file
        with open(
            "tests/files_source/software_heritage/archive_30274.zip", "rb"
        ) as open_file:
            fake_response.content = open_file.read()
        fake_requests_get.return_value = fake_response

        fake_set_resource.side_effect = Exception("Exception uploading file to bucket")

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)
