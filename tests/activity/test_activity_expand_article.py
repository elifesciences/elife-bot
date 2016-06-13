import unittest
from activity.activity_ExpandArticle import activity_ExpandArticle
from activity.activity import activity
import settings_mock
from mock import mock, patch
from testfixtures import TempDirectory
from testfixtures import tempdir, compare
import os
from classes_mock import FakeStorageContext
from classes_mock import FakeSession
import classes_mock
import test_activity_data as data

class TestExpandArticle(unittest.TestCase):
    def setUp(self):
        self.create_folder(data.ExpandArticle_files_dest_folder)
        self.expandarticle = activity_ExpandArticle(settings_mock, None, None, None, None)
        self.create_temp_folder(data.ExpandArticle_path)

    def tearDown(self):
        self.delete_files_in_folder(data.ExpandArticle_files_dest_folder)
        self.delete_folder(data.ExpandArticle_files_dest_folder)


    @patch.object(activity_ExpandArticle, 'get_tmp_dir')
    @patch('activity.activity_ExpandArticle.Session')
    @patch('activity.activity_ExpandArticle.StorageContext')
    def test_do_activity(self, mock_storage_context, mock_session, mock_get_tmp_dir):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(data.session_example)
        mock_get_tmp_dir.return_value = classes_mock.fake_get_tmp_dir(data.ExpandArticle_path)

        self.expandarticle.emit_monitor_event = mock.MagicMock()
        self.expandarticle.set_monitor_property = mock.MagicMock()

        success = self.expandarticle.do_activity(data.ExpandArticle_data)
        self.assertEqual(True, success)

        # Check destination folder as a list
        files = sorted(os.listdir(data.ExpandArticle_files_dest_folder))
        # self.assertListEqual(data.ExpandArticle_files_dest_expected, files)

        index = 0
        for file in files:
            self.assertEqual(data.ExpandArticle_files_dest_bytes_expected[index]['name'], file)
            statinfo = os.stat(data.ExpandArticle_files_dest_folder + '/' + file)
            self.assertEqual(data.ExpandArticle_files_dest_bytes_expected[index]['bytes'], statinfo.st_size)
            index += 1


    def delete_files_in_folder(self, folder):
        fileList = os.listdir(folder)
        for fileName in fileList:
            os.remove(folder+"/"+fileName)

    def create_temp_folder(self, plus=None):
        if not os.path.exists('tests/tmp'):
            os.makedirs('tests/tmp')
        if plus is not None:
            if not os.path.exists('tests/tmp/'+ data.ExpandArticle_path):
                os.makedirs('tests/tmp/' + data.ExpandArticle_path)

    def create_folder(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    def delete_folder(self, folder):
        os.rmdir(folder)



if __name__ == '__main__':
    unittest.main()
