# coding=utf-8

import os
import glob
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from ddt import ddt, data
from provider import cleaner
import activity.activity_ValidateAcceptedSubmission as activity_module
from activity.activity_ValidateAcceptedSubmission import (
    activity_ValidateAcceptedSubmission as activity_object,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity import helpers
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.test_data as test_case_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestValidateAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_log_warning_count": 2,
            "expected_email_count": 2,
            "expected_email_subject": (
                "Error validating accepted submission file: 30-01-2019-RA-eLife-45644.zip"
            ),
            "expected_email_from": "sender@example.org",
            "expected_email_body_contains": [
                "Warnings found in the log file for zip file",
                (
                    "WARNING elifecleaner:parse:check_ejp_zip: 30-01-2019-RA-eLife-45644.zip"
                    " multiple page PDF figure file:"
                ),
            ],
        },
    )
    def test_do_activity(
        self, test_data, fake_download_storage_context, fake_email_smtp_connect
    ):
        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")

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
        with open(log_file_path, "r") as open_file:
            log_contents = open_file.read()
        log_warnings = [
            line
            for line in log_contents.split("\n")
            if "WARNING elifecleaner:parse:check_ejp_zip:" in line
        ]
        self.assertEqual(len(log_warnings), test_data.get("expected_log_warning_count"))

        # check email files and contents
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0]) as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(
                        test_data.get("expected_email_subject") in first_email_content
                    )
                if test_data.get("expected_email_from"):
                    self.assertTrue(
                        test_data.get("expected_email_from") in first_email_content
                    )
                if test_data.get("expected_email_body_contains"):
                    body = helpers.body_from_multipart_email_string(first_email_content)
                    for expected_to_contain in test_data.get(
                        "expected_email_body_contains"
                    ):
                        self.assertTrue(expected_to_contain in str(body))

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(cleaner, "check_ejp_zip")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_exception_parseerror(
        self, fake_download_storage_context, fake_check_ejp_zip, fake_email_smtp_connect
    ):
        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_check_ejp_zip.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, XML ParseError exception"
                    " in cleaner.check_ejp_zip for file"
                )
            )
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(cleaner, "check_ejp_zip")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_exception_unknown(
        self, fake_download_storage_context, fake_check_ejp_zip, fake_email_smtp_connect
    ):
        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_check_ejp_zip.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ValidateAcceptedSubmission, unhandled exception"
                    " in cleaner.check_ejp_zip for file"
                )
            )
        )
