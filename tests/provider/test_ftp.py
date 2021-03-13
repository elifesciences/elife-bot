import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import ftp as ftp_provider
from tests.classes_mock import FakeFTPServer
from tests.activity.classes_mock import FakeLogger
import tests.activity.test_activity_data as testdata
from tests.activity import helpers


class TestFtpConnect(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.ftp_instance = ftp_provider.FTP(self.logger)

    @patch("ftplib.FTP")
    def test_ftp_connect(self, fake_ftp_server):
        fake_ftp_server.return_value = FakeFTPServer()
        self.assertIsNotNone(self.ftp_instance.ftp_connect(None, None, None))

    @patch("ftplib.FTP")
    def test_ftp_connect_active(self, fake_ftp_server):
        fake_ftp_server.return_value = FakeFTPServer()
        passive = False
        self.assertIsNotNone(self.ftp_instance.ftp_connect(None, None, None, passive))


class TestFtpProvider(unittest.TestCase):
    def setUp(self):
        patcher = patch("ftplib.FTP")
        fake_ftp_server = patcher.start()
        fake_ftp_server.return_value = FakeFTPServer(
            testdata.ExpandArticle_files_dest_folder
        )
        self.logger = FakeLogger()
        self.ftp_instance = ftp_provider.FTP(self.logger)
        self.ftp_connection = self.ftp_instance.ftp_connect(None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_directories_in_folder(testdata.ExpandArticle_files_dest_folder)
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    def test_ftp_disconnect(self):
        self.assertIsNone(self.ftp_instance.ftp_disconnect(self.ftp_connection))

    def test_ftp_upload_text(self):
        # create a file with a .txt extension to invoke it
        directory = TempDirectory()
        filename = directory.write("test_file.txt", "test file", encoding="utf8")
        self.ftp_instance.ftp_upload(self.ftp_connection, filename)
        uploaded_files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        self.assertTrue(filename.split("/")[-1] in uploaded_files)

    def test_ftp_upload_binary(self):
        # create a binary file to upload
        directory = TempDirectory()
        filename = directory.write("article.xml", b"<root />")
        self.ftp_instance.ftp_upload(self.ftp_connection, filename)
        uploaded_files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        self.assertTrue(filename.split("/")[-1] in uploaded_files)

    def test_ftp_cwd_mkd(self):
        # test for when folder does not initial exist, the folder will be created
        sub_dir = "test"
        self.assertFalse(self.ftp_instance.ftp_cwd_mkd(self.ftp_connection, sub_dir))
        uploaded_files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        self.assertTrue(sub_dir in uploaded_files)

    def test_ftp_cwd_mkd_folder_exists(self):
        sub_dir = "test"
        # create the folder so it already exists
        os.mkdir(os.path.join(testdata.ExpandArticle_files_dest_folder, sub_dir))
        self.assertTrue(self.ftp_instance.ftp_cwd_mkd(self.ftp_connection, sub_dir))
        uploaded_files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        self.assertTrue(sub_dir in uploaded_files)

    def test_ftp_to_endpoint(self):
        sub_dir = "test"
        directory = TempDirectory()
        filename = directory.write("article.xml", b"<root />")
        self.ftp_instance.ftp_to_endpoint(self.ftp_connection, [filename], [sub_dir])
        folder_name = os.path.join(testdata.ExpandArticle_files_dest_folder, sub_dir)
        uploaded_files = sorted(os.listdir(folder_name))
        self.assertTrue(
            filename.split("/")[-1] in uploaded_files,
            "%s not found in folder %s" % (filename.split("/")[-1], folder_name),
        )
