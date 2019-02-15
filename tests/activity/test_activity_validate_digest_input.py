# coding=utf-8

import os
import glob
import email
import unittest
from mock import patch
from ddt import ddt, data
from elifetools.utils import unicode_value
import activity.activity_ValidateDigestInput as activity_module
from activity.activity_ValidateDigestInput import activity_ValidateDigestInput as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeStorageContext


def input_data(file_name_to_change=''):
    activity_data = test_case_data.ingest_digest_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


def body_from_multipart_email_string(email_string):
    """Given a multipart email string, convert to Message and return decoded body"""
    body = None
    email_message = email.message_from_string(email_string)
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True)
    return body


@ddt
class TestValidateDigestInput(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(activity_module.digest_provider, 'storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": 'DIGEST+99999.docx',
            "expected_result": True,
            "expected_build_status": True,
            "expected_valid_status": True,
            "expected_email_status": None,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "expected_result": True,
            "expected_build_status": True,
            "expected_valid_status": True,
            "expected_email_status": None,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_digest_image_file": u'IMAGE 99999.jpeg',
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_build_status": False,
            "expected_valid_status": False,
            "expected_email_status": True,
            "expected_email_count": 1,
            "expected_email_subject": "Error processing digest file: ",
            "expected_email_from": "From: sender@example.org",
            "expected_email_body": "Digest was empty"
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_build_status": False,
            "expected_valid_status": False,
            "expected_email_status": True,
            "expected_email_count": 1,
            "expected_email_subject": "Error processing digest file: ",
            "expected_email_from": "From: sender@example.org",
            "expected_email_body": "Digest was empty"
        },
        {
            "comment": 'digest author name encoding file example',
            "filename": 'DIGEST+99997.docx',
            "expected_result": True,
            "expected_build_status": True,
            "expected_valid_status": True,
            "expected_email_status": None,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99997',
        },
        {
            "comment": 'docx file with unicode characters example',
            "filename": 'DIGEST_35774.zip',
            "expected_result": True,
            "expected_build_status": True,
            "expected_valid_status": True,
            "expected_email_status": None,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.35774',
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_email_smtp_connect):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.temp_dir)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}, got {result}, filename {filename}, ' +
                         'input_file {input_file}, digest {digest}'.format(
                             comment=test_data.get("comment"),
                             result=result,
                             input_file=self.activity.input_file,
                             filename=filename_used,
                             digest=self.activity.digest))
        self.assertEqual(self.activity.statuses.get("build"),
                         test_data.get("expected_build_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("valid"),
                         test_data.get("expected_valid_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("email"),
                         test_data.get("expected_email_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # check digest values
        if self.activity.digest and test_data.get("expected_digest_doi"):
            self.assertEqual(self.activity.digest.doi, test_data.get("expected_digest_doi"),
                             'failed in {comment}'.format(comment=test_data.get("comment")))
        # check digest image values
        if (
                self.activity.digest and self.activity.digest.image and
                test_data.get("expected_digest_image_file")):
            file_name = self.activity.digest.image.file.split(os.sep)[-1]
            self.assertEqual(file_name, test_data.get("expected_digest_image_file"),
                             'failed in {comment}'.format(comment=test_data.get("comment")))
        # check email files and contents
        email_files_filter = os.path.join(self.activity.temp_dir, "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0]) as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(test_data.get("expected_email_subject") in first_email_content)
                if test_data.get("expected_email_from"):
                    self.assertTrue(test_data.get("expected_email_from") in first_email_content)
                if test_data.get("expected_email_body"):
                    body = body_from_multipart_email_string(first_email_content)
                    self.assertTrue(test_data.get("expected_email_body") in unicode_value(body))


class TestEmailSubject(unittest.TestCase):

    def test_error_email_subject(self):
        "email subject for error emails with a unicode filename"
        filename = u'DIGESTö 99999.zip'
        expected = u'Error processing digest file: DIGESTö 99999.zip'
        subject = activity_module.error_email_subject(filename)
        self.assertEqual(subject, expected)


if __name__ == '__main__':
    unittest.main()
