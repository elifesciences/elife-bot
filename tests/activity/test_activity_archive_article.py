import os
import unittest
import zipfile
from mock import mock, patch
import activity.activity_ArchiveArticle as activity_module
from activity.activity_ArchiveArticle import activity_ArchiveArticle as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data
import tests.activity.helpers as helpers


def outbox_files(folder):
    "count the files in the folder ignoring .gitkeep or files starting with ."
    return [file_name for file_name in os.listdir(folder) if not file_name.startswith('.')]


def outbox_zip_file(folder_name):
    "zip file path in the destination folder"
    file_list = outbox_files(folder_name)
    if not file_list:
        return None
    zip_file_path = os.path.join(folder_name, file_list[0])
    return zip_file_path


class TestArchiveArticle(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=['.gitkeep'])

    def zip_assertions(self, zip_file_path, expected_zip_file_name, expected_zip_files):
        zip_file_name = None
        if zip_file_path:
            zip_file_name = zip_file_path.split(os.sep)[-1]
        self.assertEqual(zip_file_name, expected_zip_file_name)
        if zip_file_path:
            with zipfile.ZipFile(zip_file_path) as open_zip:
                self.assertEqual(sorted(open_zip.namelist()), sorted(expected_zip_files))
        else:
            self.assertEqual(None, expected_zip_files)

    @patch.object(activity_module, 'storage_context')
    def test_do_activity(self, fake_storage_context):
        expected_outbox_count = 1
        expected_zip_file_name = 'elife-00353-vor-v1-20121213000000.zip'
        expected_zip_files = [
            'elife-00353-fig1-v1.tif',
            'elife-00353-v1.xml',
            'elife-00353-v1.pdf']
        test_destination_folder = activity_test_data.ExpandArticle_files_dest_folder
        fake_storage_context.return_value = FakeStorageContext()
        self.activity.emit_monitor_event = mock.MagicMock()

        success = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(success, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(len(outbox_files(test_destination_folder)), expected_outbox_count)
        # should be one zip file
        zip_file_path = outbox_zip_file(test_destination_folder)
        self.zip_assertions(zip_file_path, expected_zip_file_name, expected_zip_files)

    @patch.object(activity_object, 'download_files')
    def test_do_activity_download_failure(self, fake_download_files):
        "test failure downloading a file"
        fake_download_files.return_value = None
        self.activity.emit_monitor_event = mock.MagicMock()
        success = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(success, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_object, 'download_files')
    def test_do_activity_major_failure(self, fake_download_files):
        "test failure of something unknown raising an exception"
        fake_download_files.side_effect = Exception("Something went wrong!")
        self.activity.emit_monitor_event = mock.MagicMock()
        success = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(success, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(FakeStorageContext, 'get_resource_to_file')
    @patch.object(FakeStorageContext, 'list_resources')
    @patch.object(activity_module, 'storage_context')
    def test_download_files_failure(
            self, fake_storage_context, fake_list_resources, fake_get_resource_to_file):
        """test exception in download_files for test coverage"""
        fake_storage_context.return_value = FakeStorageContext()
        fake_list_resources.return_value = ['fake_bucket_file.zip']
        fake_get_resource_to_file.side_effect = Exception("Something went wrong!")
        success = self.activity.download_files("bucket_name", "expanded_folder", "zip_dir_path")
        self.assertIsNone(success)


if __name__ == '__main__':
    unittest.main()
