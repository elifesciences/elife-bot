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


class TestArchiveArticle(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder(activity_test_data.ExpandArticle_files_dest_folder)

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
        zip_file_path = os.path.join(
            test_destination_folder, outbox_files(test_destination_folder)[0])
        zip_file_name = zip_file_path.split(os.sep)[-1]
        self.assertEqual(zip_file_name, expected_zip_file_name)
        with zipfile.ZipFile(zip_file_path) as open_zip:
            self.assertEqual(open_zip.namelist(), expected_zip_files)


if __name__ == '__main__':
    unittest.main()
