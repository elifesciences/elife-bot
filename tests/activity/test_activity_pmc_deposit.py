import os
import unittest
import zipfile
from mock import patch
from ddt import ddt
from testfixtures import TempDirectory
import activity.activity_PMCDeposit as activity_module
from activity.activity_PMCDeposit import activity_PMCDeposit
from tests.activity import settings_mock
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
    FakeFTP,
)


@ddt
class TestPMCDeposit(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PMCDeposit(
            settings_mock, fake_logger, None, None, None
        )
        self.activity.make_activity_directories()
        self.test_data_dir = "tests/test_data/pmc/"

        self.do_activity_passes = []

        self.do_activity_passes.append(
            {
                "scenario": "zip file was not downloaded",
                "input_data": {
                    "data": {"document": "does_not_exist.zip"},
                    "run": "test-uuid",
                },
                "pmc_zip_key_names": [],
                "related_article_json": [],
                "expected_zip_filename": None,
                "expected_result": self.activity.ACTIVITY_TEMPORARY_FAILURE,
                "zip_file_names": None,
            }
        )

        self.do_activity_passes.append(
            {
                "scenario": "no previous PMC zip file",
                "input_data": {
                    "data": {"document": "elife-19405-vor-v1-20160802113816.zip"},
                    "run": "test-uuid",
                },
                "pmc_zip_key_names": [],
                "related_article_json": [],
                "expected_zip_filename": "elife-05-19405.zip",
                "expected_result": True,
                "zip_file_names": [
                    "elife-19405-fig1.tif",
                    "elife-19405-inf1.tif",
                    "elife-19405.pdf",
                    "elife-19405.xml",
                ],
            }
        )

        self.do_activity_passes.append(
            {
                "scenario": "one previous PMC zip file",
                "input_data": {
                    "data": {"document": "elife-19405-vor-v1-20160802113816.zip"},
                    "run": "test-uuid",
                },
                "pmc_zip_key_names": ["pmc/zip/elife-05-19405.zip"],
                "related_article_json": [],
                "expected_zip_filename": "elife-05-19405.r1.zip",
                "expected_result": True,
                "zip_file_names": [
                    "elife-19405-fig1.tif",
                    "elife-19405-inf1.tif",
                    "elife-19405.pdf",
                    "elife-19405.xml",
                ],
            }
        )

        self.do_activity_passes.append(
            {
                "scenario": "two previous PMC zip file revisions present",
                "input_data": {
                    "data": {"document": "elife-19405-vor-v1-20160802113816.zip"},
                    "run": "test-uuid",
                },
                "pmc_zip_key_names": [
                    "pmc/zip/elife-05-19405.zip",
                    "pmc/zip/elife-05-19405.r1.zip",
                ],
                "related_article_json": [],
                "expected_zip_filename": "elife-05-19405.r2.zip",
                "expected_result": True,
                "zip_file_names": [
                    "elife-19405-fig1.tif",
                    "elife-19405-inf1.tif",
                    "elife-19405.pdf",
                    "elife-19405.xml",
                ],
            }
        )

        self.do_activity_passes.append(
            {
                "scenario": "retracted article",
                "input_data": {
                    "data": {"document": "elife-19405-vor-v1-20160802113816.zip"},
                    "run": "test-uuid",
                },
                "pmc_zip_key_names": [],
                "related_article_json": [{"type": "retraction"}],
                "expected_zip_filename": "elife-05-19405.zip",
                "expected_result": True,
                "zip_file_names": [
                    "elife-19405-fig1.tif",
                    "elife-19405-inf1.tif",
                    "elife-19405.pdf",
                    "elife-19405.xml",
                ],
            }
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def zip_file_list(self, zip_file_name):
        file_list = None
        zip_file_path = (
            self.activity.directories.get("ZIP_DIR") + os.sep + zip_file_name
        )
        with zipfile.ZipFile(zip_file_path, "r") as open_zip_file:
            file_list = open_zip_file.namelist()
        return file_list

    @patch.object(activity_PMCDeposit, "clean_tmp_dir")
    @patch("provider.lax_provider.article_related")
    @patch("activity.activity_PMCDeposit.FTP")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("activity.activity_PMCDeposit.storage_context")
    def test_do_activity(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_ftp,
        mock_article_related,
        fake_clean_tmp_dir,
    ):
        directory = TempDirectory()
        fake_ftp.return_value = FakeFTP()
        fake_clean_tmp_dir.return_value = None

        for test_data in self.do_activity_passes:

            fake_storage_context.return_value = FakeStorageContext(
                directory=self.test_data_dir, dest_folder=directory.path
            )
            fake_list_resources.return_value = test_data["pmc_zip_key_names"]
            mock_article_related.return_value = 200, test_data["related_article_json"]

            success = self.activity.do_activity(test_data["input_data"])

            self.assertEqual(
                success,
                test_data["expected_result"],
                "{value} does not equal {expected}, scenario: {scenario}".format(
                    value=success,
                    expected=test_data["expected_result"],
                    scenario=test_data["scenario"],
                ),
            )
            self.assertEqual(
                self.activity.zip_file_name, test_data["expected_zip_filename"]
            )
            if test_data["zip_file_names"]:
                self.assertEqual(
                    sorted(self.zip_file_list(self.activity.zip_file_name)),
                    sorted(test_data["zip_file_names"]),
                )

    @patch("provider.lax_provider.article_related")
    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_PMCDeposit, "ftp_to_endpoint")
    @patch("activity.activity_PMCDeposit.storage_context")
    def test_do_activity_no_settings_uri(
        self,
        fake_storage_context,
        fake_ftp_to_endpoint,
        fake_list_resources,
        mock_article_related,
    ):
        "test for when the PMC_FTP_URI is blank"
        self.activity.settings.PMC_FTP_URI = ""
        test_data = self.do_activity_passes[1]
        result = self.activity.do_activity(test_data["input_data"])
        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, result)

    @patch("provider.lax_provider.article_related")
    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_PMCDeposit, "ftp_to_endpoint")
    @patch("activity.activity_PMCDeposit.storage_context")
    def test_do_activity_lax_failure(
        self,
        fake_storage_context,
        fake_ftp_to_endpoint,
        fake_list_resources,
        mock_article_related,
    ):

        test_data = self.do_activity_passes[1]

        fake_storage_context.return_value = FakeStorageContext(
            directory=self.test_data_dir
        )
        fake_list_resources.return_value = test_data["pmc_zip_key_names"]
        fake_ftp_to_endpoint.return_value = None
        mock_article_related.return_value = 404, None

        success = self.activity.do_activity(test_data["input_data"])

        self.assertEqual(self.activity.ACTIVITY_TEMPORARY_FAILURE, success)

    @patch("provider.lax_provider.article_related")
    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_PMCDeposit, "ftp_to_endpoint")
    @patch("activity.activity_PMCDeposit.storage_context")
    def test_do_activity_failed_ftp_to_endpoint(
        self,
        fake_storage_context,
        fake_ftp_to_endpoint,
        fake_list_resources,
        mock_article_related,
    ):

        test_data = self.do_activity_passes[1]

        fake_storage_context.return_value = FakeStorageContext(
            directory=self.test_data_dir
        )
        fake_list_resources.return_value = test_data["pmc_zip_key_names"]
        fake_ftp_to_endpoint.return_value = None
        mock_article_related.return_value = 200, []

        success = self.activity.do_activity(test_data["input_data"])

        self.assertEqual(False, success)

    @patch("provider.lax_provider.article_related")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("activity.activity_PMCDeposit.get_session")
    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_PMCDeposit, "ftp_to_endpoint")
    @patch("activity.activity_PMCDeposit.storage_context")
    def test_do_activity_ftp_to_endpoint_exception(
        self,
        fake_storage_context,
        fake_ftp_to_endpoint,
        fake_list_resources,
        fake_session,
        fake_email_smtp_connect,
        mock_article_related,
    ):
        directory = TempDirectory()
        test_data = self.do_activity_passes[1]
        fake_session.return_value = FakeSession({})
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        fake_storage_context.return_value = FakeStorageContext(
            directory=self.test_data_dir
        )
        fake_list_resources.return_value = test_data["pmc_zip_key_names"]
        fake_ftp_to_endpoint.side_effect = Exception("An exception")
        mock_article_related.return_value = 200, []

        success = self.activity.do_activity(test_data["input_data"])

        self.assertEqual(self.activity.ACTIVITY_TEMPORARY_FAILURE, success)
        self.assertEqual(
            str(self.activity.logger.logexception),
            (
                "Exception in ftp_to_endpoint sending file elife-05-19405.zip: An exception"
            ),
        )


class TestFtpToEndpoint(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.activity = activity_PMCDeposit(
            settings_mock, self.fake_logger, None, None, None
        )
        self.test_data_dir = "tests/test_data/pmc/"

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.FTP, "ftp_connect")
    def test_ftp_to_endpoint_connect_exception(self, fake_ftp_connect):
        fake_ftp_connect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.test_data_dir)
        self.assertEqual(
            str(self.activity.logger.logexception),
            ("Exception connecting to FTP server: An exception"),
        )

    @patch.object(activity_module.FTP, "ftp_disconnect")
    @patch.object(activity_module.FTP, "ftp_to_endpoint")
    @patch.object(activity_module.FTP, "ftp_connect")
    def test_ftp_to_endpoint_transfer_exception(
        self, fake_ftp_connect, fake_ftp_to_endpoint, fake_ftp_disconnect
    ):
        fake_ftp_connect.return_value = True
        fake_ftp_disconnect.return_value = True
        fake_ftp_to_endpoint.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.test_data_dir)
        self.assertEqual(
            str(self.activity.logger.logexception),
            ("Exception in transfer of files by FTP: An exception"),
        )

    @patch.object(activity_module.FTP, "ftp_disconnect")
    @patch.object(activity_module.FTP, "ftp_to_endpoint")
    @patch.object(activity_module.FTP, "ftp_connect")
    def test_ftp_to_endpoint_disconnect_exception(
        self, fake_ftp_connect, fake_ftp_to_endpoint, fake_ftp_disconnect
    ):
        fake_ftp_connect.return_value = True
        fake_ftp_to_endpoint.return_value = True
        fake_ftp_disconnect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.test_data_dir)
        self.assertEqual(
            str(self.activity.logger.logexception),
            ("Exception disconnecting from FTP server: An exception"),
        )
