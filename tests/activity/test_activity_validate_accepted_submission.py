# coding=utf-8

import os
import glob
import shutil
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_ValidateAcceptedSubmission as activity_module
from activity.activity_ValidateAcceptedSubmission import (
    activity_ValidateAcceptedSubmission as activity_object,
)
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestValidateAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(test_activity_data.valid_accepted_session_example)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_log_warning_count": 2,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        # expanded bucket files
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            test_data.get("filename"),
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_session.return_value = self.session
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")

        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            (
                "failed in {comment}, got {result}, filename {filename}, "
                + "input_file {input_file}"
            ).format(
                comment=test_data.get("comment"),
                result=result,
                input_file=self.activity.input_file,
                filename=filename_used,
            ),
        )

        self.assertEqual(
            self.activity.statuses.get("valid"),
            test_data.get("expected_valid_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        log_warnings = [
            line
            for line in log_contents.split("\n")
            if "WARNING elifecleaner:parse:check_multi_page_figure_pdf:" in line
        ]
        self.assertEqual(len(log_warnings), test_data.get("expected_log_warning_count"))

        # check session prc value
        self.assertEqual(self.session.get_value("prc_status"), False)

        # check session cleaner_log contains content
        self.assertTrue("elifecleaner:parse:" in self.session.get_value("cleaner_log"))

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "file_list")
    def test_do_activity_exception_parseerror(
        self,
        fake_file_list,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()

        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_file_list.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, True)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, XML ParseError exception"
                    " in cleaner.file_list parsing XML file"
                    " 30-01-2019-RA-eLife-45644.xml for file"
                )
            )
        )
        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        log_errors = [
            line for line in log_contents.split("\n") if "ERROR elifecleaner:" in line
        ]
        self.assertEqual(len(log_errors), 1)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "check_files")
    def test_do_activity_exception_unknown(
        self,
        fake_check_files,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()

        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_check_files.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, True)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, unhandled exception"
                    " in cleaner.check_files for file"
                )
            )
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "preprint_url")
    def test_do_activity_prc(
        self,
        fake_preprint_url,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()
        self.session.store_value("prc_status", True)
        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_preprint_url.return_value = "https://doi.org/10.1101/2021.06.02.446694"
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, True)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "preprint_url")
    def test_do_activity_prc_sciety_failure(
        self,
        fake_preprint_url,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()
        self.session.store_value("prc_status", True)
        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        # empty the docmap_string value in the session
        self.session.store_value("docmap_string", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        preprint_doi = "10.1101/2021.06.02.999999"
        fake_preprint_url.return_value = "https://doi.org/%s" % preprint_doi
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        # assertions for activity log
        self.assertEqual(
            self.activity.logger.loginfo[-2],
            (
                "ValidateAcceptedSubmission, docmap_string from the session was missing or blank"
            ),
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "preprint_url")
    def test_do_activity_prc_no_preprint_url(
        self,
        fake_preprint_url,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()

        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_preprint_url.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, True)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "preprint_url")
    def test_do_activity_preprint_url_exception(
        self,
        fake_preprint_url,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        self.session.store_value("prc_status", False)
        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_preprint_url.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, True)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, XML ParseError exception"
                    " in cleaner.preprint_url parsing XML file"
                    " 30-01-2019-RA-eLife-45644.xml for file"
                )
            )
        )
        # assertions for cleaner.log
        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        log_errors = [
            line for line in log_contents.split("\n") if "ERROR elifecleaner:" in line
        ]
        self.assertEqual(len(log_errors), 1)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "parse_article_xml")
    def test_do_activity_xml_parsing_exception(
        self,
        fake_parse_article_xml,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()

        # set a non-None session value to test string concatenation
        self.session.store_value("cleaner_log", "")
        fake_session.return_value = self.session
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            "30-01-2019-RA-eLife-45644.zip",
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_parse_article_xml.side_effect = ParseError()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, XML ParseError exception"
                    " parsing XML file"
                    " 30-01-2019-RA-eLife-45644.xml for file"
                )
            )
        )


class TestErrorEmailSubject(unittest.TestCase):
    def test_error_email_subject(self):
        "email subject line with correct output_file value"

        class continuumtest:
            "mock settings object for testing"
            pass

        output_file = "file.zip"
        expected = "TEST Error validating accepted submission file: %s" % output_file
        subject = activity_module.error_email_subject(output_file, continuumtest)
        self.assertEqual(subject, expected)

    def test_no_settings_class_name(self):
        "test if the settings is not a class"
        output_file = "file.zip"
        expected = "Error validating accepted submission file: %s" % output_file
        subject = activity_module.error_email_subject(output_file, settings_mock)
        self.assertEqual(subject, expected)

    def test_settings_none(self):
        "test if settings is not passed as an argument"
        output_file = "file.zip"
        expected = "Error validating accepted submission file: %s" % output_file
        subject = activity_module.error_email_subject(output_file)
        self.assertEqual(subject, expected)
