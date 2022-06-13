# coding=utf-8

import os
import glob
import unittest
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
import activity.activity_ValidateDecisionLetterInput as activity_module
from activity.activity_ValidateDecisionLetterInput import (
    activity_ValidateDecisionLetterInput as activity_object,
)
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
from tests.activity import helpers, settings_mock
from tests.activity.classes_mock import FakeStorageContext


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_decision_letter_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestValidateDecisionLetterInput(unittest.TestCase):
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
            "comment": "decision letter zip file example",
            "filename": "elife-39122.zip",
            "expected_result": True,
            "expected_check_input_status": True,
            "expected_unzip_status": True,
            "expected_build_status": True,
            "expected_valid_status": True,
            "expected_generate_status": True,
            "expected_output_status": True,
            "expected_chars_status": True,
            "expected_email_status": None,
            "expected_doi_0": "10.7554/eLife.39122.sa1",
            "expected_digest_image_file": "IMAGE 99999.jpeg",
        },
        {
            "comment": "file does not exist example",
            "filename": "",
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_check_input_status": False,
            "expected_unzip_status": None,
            "expected_build_status": None,
            "expected_valid_status": None,
            "expected_generate_status": None,
            "expected_output_status": None,
            "expected_chars_status": None,
            "expected_email_status": True,
            "expected_email_count": 1,
            "expected_email_subject": "Error processing decision letter file: ",
            "expected_email_from": "From: sender@example.org",
            "expected_email_body": "File None does not exist",
        },
    )
    def test_do_activity(
        self, test_data, fake_download_storage_context, fake_email_smtp_connect
    ):
        # copy XML files into the input directory using the storage context
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

        # check assertions on status values
        status_map = OrderedDict(
            [
                ("check_input", "expected_check_input_status"),
                ("unzip", "expected_unzip_status"),
                ("build", "expected_build_status"),
                ("valid", "expected_valid_status"),
                ("generate", "expected_generate_status"),
                ("output", "expected_output_status"),
                ("chars", "expected_chars_status"),
                ("email", "expected_email_status"),
            ]
        )
        for status, expected in status_map.items():
            self.assertEqual(
                self.activity.statuses.get(status),
                test_data.get(expected),
                "failed checking {status} status in {comment}".format(
                    status=status, comment=test_data.get("comment")
                ),
            )

        # check article values
        if test_data.get("expected_doi_0"):
            self.assertEqual(
                self.activity.articles[0].doi,
                test_data.get("expected_doi_0"),
                "failed in {comment}".format(comment=test_data.get("comment")),
            )

        # check email files and contents
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0], encoding="utf8") as open_file:
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
                if test_data.get("expected_email_body"):
                    body = helpers.body_from_multipart_email_string(first_email_content)
                    self.assertTrue(test_data.get("expected_email_body") in str(body))

    @patch.object(activity_module.letterparser_provider.zip_lib, "unzip_zip")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_unzip_false(
        self, fake_download_storage_context, fake_email_smtp_connect, fake_unzip_zip
    ):
        "test if the unzip status is not True"
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_unzip_zip.side_effect = Exception("An exception")
        result = self.activity.do_activity(input_data("elife-39122.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_module.letterparser_provider, "output_xml")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_chars_not_valid(
        self, fake_download_storage_context, fake_email_smtp_connect, fake_output_xml
    ):
        "test if there is a potential problem character in the XML"
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_output_xml.return_value = True, "<article><p>\u2028</p></article>"
        result = self.activity.do_activity(input_data("elife-39122.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        # check email files and contents
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)

        # can look at the first email for the subject and sender
        first_email_content = None
        with open(email_files[0], encoding="utf8") as open_file:
            first_email_content = open_file.read()
        if first_email_content:
            self.assertTrue(
                "Error processing decision letter file: " in first_email_content
            )
            body = helpers.body_from_multipart_email_string(first_email_content)
            print(body)
            self.assertTrue(
                (
                    b"Detected potentially incompatible characters in the JATS XML\n\n"
                    b"\xe2\x80\xa8 (LINE SEPARATOR)\n"
                    b"\n<article><p>\xe2\x80\xa8</p></article>"
                )
                in body
            )


class TestEmailSubject(unittest.TestCase):
    def test_error_email_subject(self):
        "email subject for error emails with a unicode filename"
        filename = "elife-99999.zip"
        expected = "Error processing decision letter file: elife-99999.zip"
        subject = activity_module.error_email_subject(filename)
        self.assertEqual(subject, expected)
