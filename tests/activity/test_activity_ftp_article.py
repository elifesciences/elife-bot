import unittest
import shutil
import os
import zipfile
import datetime
from mock import MagicMock, patch
from ddt import ddt, data, unpack
from provider.sftp import SFTP
import activity.activity_FTPArticle as activity_module
from activity.activity_FTPArticle import activity_FTPArticle
from tests.activity.classes_mock import FakeFTP, FakeLogger, FakeStorageContext
from tests.activity import settings_mock, test_activity_data


class FakeSFTP:
    "mock the provider.sftp.SFTP class for when testing"

    def sftp_connect(self, *args):
        return True

    def sftp_to_endpoint(self, *args):
        return True

    def disconnect(self):
        return True


@ddt
class TestFTPArticle(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_FTPArticle, "repackage_archive_zip_to_pmc_zip")
    @patch.object(activity_FTPArticle, "download_archive_zip_from_s3")
    @patch("activity.activity_FTPArticle.FTP")
    @patch("activity.activity_FTPArticle.SFTP")
    @data(
        ("HEFCE", True, "hefce_ftp.localhost", "hefce_sftp.localhost", 1, True),
        ("Cengage", True, "cengage.localhost", None, 1, True),
        ("GoOA", True, "gooa.localhost", None, 1, True),
        ("WoS", True, "wos.localhost", None, 1, True),
        ("CNPIEC", True, "cnpiec.localhost", None, 1, True),
        ("CNKI", True, "cnki.localhost", None, 1, True),
        ("CLOCKSS", True, "clockss.localhost", None, 1, True),
        ("OVID", True, "ovid.localhost", None, 1, True),
        ("Zendy", True, None, "zendy.localhost", 1, True),
        ("OASwitchboard", True, None, "oaswitchboard.localhost", 1, True),
        ("__unknown__", False, None, None, 0, False),
    )
    @unpack
    def test_do_activity(
        self,
        workflow,
        archive_zip_return_value,
        expected_ftp_uri,
        expected_sftp_uri,
        expected_sending_started_messages,
        expected_result,
        fake_sftp,
        fake_ftp,
        fake_download_archive_zip_from_s3,
        fake_repackage_pmc_zip,
    ):
        fake_sftp.return_value = FakeSFTP()
        fake_ftp.return_value = FakeFTP()
        fake_download_archive_zip_from_s3.return_value = archive_zip_return_value
        fake_repackage_pmc_zip.return_value = True
        activity_data = {"data": {"elife_id": "19405", "workflow": workflow}}
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)
        self.assertEqual(self.activity.FTP_URI, expected_ftp_uri)
        self.assertEqual(self.activity.SFTP_URI, expected_sftp_uri)
        # check log for started ftp_to_endpoint() or started sftp_to_endpoint()
        log_sending_started_messages = [
            message
            for message in self.activity.logger.loginfo
            if "started ftp_to_endpoint()" in message
            or "started sftp_to_endpoint()" in message
        ]
        self.assertEqual(
            len(log_sending_started_messages),
            expected_sending_started_messages,
            "info log did not contain started message for workflow %s" % workflow,
        )

    def test_do_activity_no_ftp_uri(
        self,
    ):
        "test for when the FTP_URI is blank"
        self.activity.settings.CENGAGE_FTP_URI = ""
        workflow = "Cengage"
        elife_id = "19405"
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        activity_data = {"data": {"elife_id": elife_id, "workflow": workflow}}
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)

    def test_do_activity_no_sftp_uri(
        self,
    ):
        "test for when the SFTP_URI is blank"
        self.activity.settings.HEFCE_SFTP_URI = ""
        workflow = "HEFCE"
        elife_id = "19405"
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        activity_data = {"data": {"elife_id": elife_id, "workflow": workflow}}
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)

    @patch.object(activity_FTPArticle, "download_files_from_s3")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    def test_do_activity_failure(
        self,
        fake_sftp_to_endpoint,
        fake_download_files_from_s3,
    ):
        fake_sftp_to_endpoint.return_value = True
        fake_download_files_from_s3.return_value = True
        workflow = "HEFCE"
        elife_id = "non_numeric_raises_exception"
        expected_result = False
        # Cause an exception by setting elife_id as non numeric for now
        activity_data = {"data": {"elife_id": elife_id, "workflow": workflow}}
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)

    @patch.object(activity_FTPArticle, "download_files_from_s3")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    def test_do_activity_exception(
        self,
        fake_sftp_to_endpoint,
        fake_download_files_from_s3,
    ):
        fake_sftp_to_endpoint.side_effect = Exception("An exception")
        fake_download_files_from_s3.return_value = True
        workflow = "HEFCE"
        elife_id = "19405"
        expected_result = False
        # Cause an exception by setting elife_id as non numeric for now
        activity_data = {"data": {"elife_id": elife_id, "workflow": workflow}}
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)


class TestDownloadFilesFromS3(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_FTPArticle, "repackage_archive_zip_to_pmc_zip")
    @patch.object(activity_FTPArticle, "download_archive_zip_from_s3")
    def test_download_files_from_s3_failure(
        self, fake_download_archive_zip, fake_repackage_archive_zip
    ):
        fake_download_archive_zip.return_value = True
        fake_repackage_archive_zip.return_value = False
        doi_id = "353"
        workflow = "HEFCE"
        # invoke the method being tested
        self.activity.download_files_from_s3(doi_id, workflow)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "FTPArticle running %s workflow for article %s, failed to package any zip files"
            )
            % (workflow, doi_id),
        )


class TestDownloadArchiveZip(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "storage_context")
    def test_download_archive_zip_from_s3(self, fake_storage_context):
        self.activity.make_activity_directories()
        # create mock Key object with name and last_modified value
        doi_id = "353"
        zip_file_name = "elife-00353-vor-v1-20121213000000.zip"
        resources = [
            {"Key": zip_file_name, "LastModified": datetime.datetime(2019, 5, 31)}
        ]
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder, resources
        )
        self.assertEqual(self.activity.download_archive_zip_from_s3(doi_id), True)
        self.assertEqual(
            self.activity.logger.loginfo[1],
            ("Latest archive zip for status vor, doi id %s, is s3 key name %s")
            % (doi_id, zip_file_name),
        )
        self.assertEqual(
            os.listdir(self.activity.directories.get("TMP_DIR")),
            [zip_file_name],
        )

    @patch.object(activity_module, "storage_context")
    def test_download_archive_zip_from_s3_no_key_found(self, fake_storage_context):
        self.activity.make_activity_directories()
        # create mock Key object with name and last_modified value
        doi_id = "353"
        resources = []
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder, resources
        )
        self.assertEqual(self.activity.download_archive_zip_from_s3(doi_id), False)
        self.assertEqual(
            self.activity.logger.loginfo[1],
            ("For archive zip for status vor, doi id %s, no s3 key name was found")
            % doi_id,
        )


@ddt
class TestMoveOrRepackagePmcZip(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @data(
        (
            "tests/test_data/pmc/elife-05-19405.zip",
            19405,
            "Cengage",
            "elife-19405-xml-pdf.zip",
            ["elife-19405.pdf", "elife-19405.xml"],
        ),
        (
            "tests/test_data/pmc/elife-05-19405.zip",
            19405,
            "HEFCE",
            "elife-05-19405.zip",
            [
                "elife-19405.pdf",
                "elife-19405.xml",
                "elife-19405-inf1.tif",
                "elife-19405-fig1.tif",
            ],
        ),
        (
            "tests/test_data/pmc/elife-05-19405.zip",
            19405,
            "CNKI",
            "elife-19405-xml.zip",
            ["elife-19405.xml"],
        ),
    )
    @unpack
    def test_move_or_repackage_pmc_zip(
        self,
        input_zip_file_path,
        doi_id,
        workflow,
        expected_zip_file,
        expected_zip_file_contents,
    ):
        # create activity directories
        self.activity.make_activity_directories()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"),
            input_zip_file_path.rsplit("/", 1)[-1],
        )
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        # call the activity function
        self.activity.move_or_repackage_pmc_zip(doi_id, workflow)
        # confirm the output
        ftp_outbox_dir = self.activity.directories.get("FTP_TO_SOMEWHERE_DIR")
        self.assertTrue(expected_zip_file in os.listdir(ftp_outbox_dir))
        with zipfile.ZipFile(
            os.path.join(ftp_outbox_dir, expected_zip_file)
        ) as zip_file:
            self.assertEqual(
                sorted(zip_file.namelist()), sorted(expected_zip_file_contents)
            )


class TestRepackagePmcZip(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_repackage_pmc_zip(
        self,
    ):
        doi_id = 19405
        zip_file_list = ["test.pdf", "test.xml", "test-code.pdf"]
        keep_file_types = ["pdf", "xml"]
        expected_zip_file = "elife-19405-pdf-xml.zip"
        expected_zip_file_contents = ["test.pdf", "test.xml"]
        # create activity directories
        self.activity.make_activity_directories()
        # create a sample intput zip file
        input_zip_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"), "test.zip"
        )
        with zipfile.ZipFile(
            input_zip_file_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as zip_file:
            for filename in zip_file_list:
                zip_file.writestr(filename, "")

        # call the activity function
        self.activity.repackage_pmc_zip(doi_id, keep_file_types)
        with zipfile.ZipFile(
            os.path.join(
                self.activity.directories.get("FTP_TO_SOMEWHERE_DIR"), expected_zip_file
            )
        ) as zip_file:
            self.assertEqual(
                sorted(zip_file.namelist()), sorted(expected_zip_file_contents)
            )


class TestRepackageArchiveZip(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def test_repackage_archive_zip_to_pmc_zip(self):
        input_zip_file_path = (
            "tests/test_data/pmc/elife-19405-vor-v1-20160802113816.zip"
        )
        doi_id = 19405
        # create activity directories
        self.activity.make_activity_directories()
        zip_renamed_files_dir = os.path.join(
            self.activity.directories.get("TMP_DIR"), "rename_dir"
        )
        pmc_zip_output_dir = self.activity.directories.get("INPUT_DIR")
        expected_pmc_zip_file = os.path.join(pmc_zip_output_dir, "elife-05-19405.zip")
        expected_article_xml_file = os.path.join(
            zip_renamed_files_dir, "elife-19405.xml"
        )
        expected_article_xml_string = b"elife-19405.pdf"
        expected_pmc_zip_file_contents = [
            "elife-19405.pdf",
            "elife-19405.xml",
            "elife-19405-inf1.tif",
            "elife-19405-fig1.tif",
        ]
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.directories.get("TMP_DIR"),
            input_zip_file_path.rsplit("/", 1)[-1],
        )
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        self.activity.repackage_archive_zip_to_pmc_zip(doi_id)
        # now can check the results
        self.assertTrue(os.path.exists(expected_pmc_zip_file))
        self.assertTrue(os.path.exists(expected_article_xml_file))
        with open(expected_article_xml_file, "rb") as open_file:
            # check for a renamed file in the XML contents
            self.assertTrue(expected_article_xml_string in open_file.read())
        with zipfile.ZipFile(expected_pmc_zip_file) as zip_file:
            # check pmc zip file contents
            self.assertEqual(
                sorted(zip_file.namelist()), sorted(expected_pmc_zip_file_contents)
            )


class TestFTPArticleFTPToEndpoint(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )
        self.activity.FTP_URI = "ftp.example.org"
        self.activity.FTP_CWD = "folder"
        self.uploadfiles = ["zipfile.zip"]
        self.sub_dir_list = ["subfolder", "subsubfolder"]

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(FakeFTP, "ftp_connect")
    @patch("activity.activity_FTPArticle.FTP")
    def test_ftp_connect_exception(self, fake_ftp, fake_ftp_connect):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_connect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles)
        self.assertEqual(
            self.activity.logger.logexception,
            "Exception connecting to FTP server ftp.example.org: An exception",
        )

    @patch.object(FakeFTP, "ftp_upload")
    @patch("activity.activity_FTPArticle.FTP")
    def test_ftp_upload_exception(self, fake_ftp, fake_ftp_upload):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_upload.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles, self.sub_dir_list)
        self.assertEqual(
            self.activity.logger.logexception,
            "Exception in uploading file zipfile.zip by FTP in FTPArticle: An exception",
        )

    @patch.object(FakeFTP, "ftp_disconnect")
    @patch("activity.activity_FTPArticle.FTP")
    def test_ftp_disconnect_exception(self, fake_ftp, fake_ftp_disconnect):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_disconnect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles)
        self.assertEqual(
            self.activity.logger.logexception,
            "Exception disconnecting from FTP server ftp.example.org: An exception",
        )


class TestSFTPToEndpoint(unittest.TestCase):
    def setUp(self):
        self.activity = activity_FTPArticle(
            settings_mock, FakeLogger(), None, None, None
        )
        self.activity.SFTP_URI = "ftp.example.org"
        self.activity.SFTP_USERNAME = ""
        self.activity.SFTP_PASSWORD = ""
        self.activity.SFTP_CWD = "folder"
        self.uploadfiles = ["zipfile.zip"]

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(SFTP, "disconnect")
    @patch.object(SFTP, "sftp_to_endpoint")
    @patch.object(SFTP, "sftp_connect")
    def test_sftp_connect(
        self, fake_sftp_connect, fake_sftp_to_endpoint, fake_disconnect
    ):
        fake_sftp_connect.return_value = MagicMock()
        fake_sftp_to_endpoint.return_value = True
        fake_disconnect.return_value = MagicMock()
        self.activity.sftp_to_endpoint(self.uploadfiles)
        fake_sftp_connect.assert_called_with(
            self.activity.SFTP_URI,
            self.activity.SFTP_USERNAME,
            self.activity.SFTP_PASSWORD,
        )
        fake_disconnect.assert_called_with()

    @patch.object(SFTP, "sftp_to_endpoint")
    @patch.object(SFTP, "sftp_connect")
    def test_sftp_to_endpoint(self, fake_sftp_connect, fake_sftp_to_endpoint):
        fake_sftp_connect.return_value = True
        fake_sftp_to_endpoint.return_value = MagicMock()
        self.activity.sftp_to_endpoint(self.uploadfiles)
        fake_sftp_to_endpoint.assert_called_with(True, ["zipfile.zip"], "folder", None)


@ddt
class TestZipFileSuffix(unittest.TestCase):
    @data(
        (["xml", "pdf"], "-xml-pdf.zip"),
        (["xml"], "-xml.zip"),
    )
    @unpack
    def test_zip_file_suffix(self, file_types, expected):
        self.assertEqual(activity_module.zip_file_suffix(file_types), expected)


@ddt
class TestNewZipFileName(unittest.TestCase):
    @data(
        (666, "elife-", "-xml-pdf.zip", "elife-00666-xml-pdf.zip"),
    )
    @unpack
    def test_zip_file_suffix(self, doi_id, prefix, suffix, expected):
        self.assertEqual(
            activity_module.new_zip_file_name(doi_id, prefix, suffix), expected
        )


@ddt
class TestFileTypeMatches(unittest.TestCase):
    @data(
        (["xml", "pdf"], ["/*.xml", "/*.pdf"]),
        (["xml"], ["/*.xml"]),
    )
    @unpack
    def test_file_type_matches(self, file_types, expected):
        self.assertEqual(activity_module.file_type_matches(file_types), expected)
