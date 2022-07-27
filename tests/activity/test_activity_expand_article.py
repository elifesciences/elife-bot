import os
import unittest
from mock import mock, patch
from testfixtures import TempDirectory
from ddt import ddt, data
from activity.activity_ExpandArticle import activity_ExpandArticle
from tests.activity import classes_mock, helpers, settings_mock
from tests.activity.classes_mock import FakeStorageContext, FakeSession
import tests.activity.test_activity_data as testdata


@ddt
class TestExpandArticle(unittest.TestCase):
    def setUp(self):
        self.expandarticle = activity_ExpandArticle(
            settings_mock, None, None, None, None
        )
        self.create_temp_folder(testdata.ExpandArticle_path)

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_directories_in_folder("tests/tmp")
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])
        self.expandarticle.clean_tmp_dir()

    @patch.object(activity_ExpandArticle, "get_tmp_dir")
    @patch("activity.activity_ExpandArticle.get_session")
    @patch("activity.activity_ExpandArticle.storage_context")
    def test_do_activity(self, mock_storage_context, mock_session, mock_get_tmp_dir):
        directory = TempDirectory()
        mock_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        mock_session.return_value = FakeSession(testdata.session_example)
        mock_get_tmp_dir.return_value = classes_mock.fake_get_tmp_dir(
            testdata.ExpandArticle_path
        )

        self.expandarticle.emit_monitor_event = mock.MagicMock()
        self.expandarticle.set_monitor_property = mock.MagicMock()
        self.expandarticle.logger = mock.MagicMock()

        success = self.expandarticle.do_activity(testdata.ExpandArticle_data)
        self.assertEqual(True, success)

        # Check destination folder as a list
        bucket_folder_path = os.path.join(
            directory.path,
            testdata.session_example.get("expanded_folder"),
        )
        files = sorted(os.listdir(bucket_folder_path))

        index = 0
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        for file in compare_files:
            self.assertEqual(
                testdata.ExpandArticle_files_dest_bytes_expected[index]["name"], file
            )
            statinfo = os.stat(bucket_folder_path + "/" + file)
            self.assertEqual(
                testdata.ExpandArticle_files_dest_bytes_expected[index]["bytes"],
                statinfo.st_size,
            )
            index += 1

    @patch("activity.activity_ExpandArticle.get_session")
    @patch("activity.activity_ExpandArticle.storage_context")
    def test_do_activity_invalid_articleid(self, mock_storage_context, mock_session):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(testdata.session_example)

        self.expandarticle.logger = mock.MagicMock()
        self.expandarticle.emit_monitor_event = mock.MagicMock()
        self.expandarticle.set_monitor_property = mock.MagicMock()

        success = self.expandarticle.do_activity(
            testdata.ExpandArticle_data_invalid_article
        )
        self.assertEqual(self.expandarticle.ACTIVITY_PERMANENT_FAILURE, success)

    @patch("activity.activity_ExpandArticle.get_session")
    @patch("activity.activity_ExpandArticle.storage_context")
    @data(
        testdata.ExpandArticle_data_invalid_status1_session_example,
        testdata.ExpandArticle_data_invalid_status2_session_example,
    )
    def test_do_activity_invalid_status(
        self, session_example, mock_storage_context, mock_session
    ):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(session_example)

        self.expandarticle.logger = mock.MagicMock()
        self.expandarticle.emit_monitor_event = mock.MagicMock()
        self.expandarticle.set_monitor_property = mock.MagicMock()

        success = self.expandarticle.do_activity(
            testdata.ExpandArticle_data_invalid_status
        )
        self.assertEqual(self.expandarticle.ACTIVITY_PERMANENT_FAILURE, success)

    def test_check_filenames(self):
        self.expandarticle.check_filenames(["elife-12345-vor.xml"])
        self.expandarticle.check_filenames(
            ["elife-12345-vor.xml", "elife-12345-vor.pdf"]
        )
        with self.assertRaises(RuntimeError):
            self.expandarticle.check_filenames(["elife-12345"])

    def create_temp_folder(self, plus=None):
        if not os.path.exists("tests/tmp"):
            os.makedirs("tests/tmp")
        if plus is not None:
            if not os.path.exists("tests/tmp/" + testdata.ExpandArticle_path):
                os.makedirs("tests/tmp/" + testdata.ExpandArticle_path)


if __name__ == "__main__":
    unittest.main()
