# coding=utf-8

import os
import glob
import unittest
from mock import patch
from ddt import ddt, data
from digestparser.objects import Digest
import activity.activity_EmailDigest as activity_module
from activity.activity_EmailDigest import activity_EmailDigest as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeStorageContext


def input_data(file_name_to_change=None):
    activity_data = test_case_data.ingest_digest_data
    if file_name_to_change is not None:
        activity_data["file_name"] = file_name_to_change
    return activity_data


def list_test_dir(dir_name, ignore=('.keepme')):
    "list the contents of a directory ignoring the ignore files"
    file_names = os.listdir(dir_name)
    return [file_name for file_name in file_names if file_name not in ignore]


@ddt
class TestEmailDigest(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('activity.activity_EmailDigest.storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": None,
            "expected_result": True,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_generate_status": True,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_output_dir_files": ['Anonymous_99999.docx'],
            "expected_email_count": 2,
            "expected_email_subject": "Subject: Digest: Anonymous_99999",
            "expected_email_from": "From: sender@example.org"
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "expected_result": True,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_generate_status": True,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_digest_image_file": u'IMAGE 99999.jpeg',
            "expected_output_dir_files": ['Anonymous_99999.docx'],
            "expected_email_count": 2,
            "expected_email_subject": "Subject: Digest: Anonymous_99999",
            "expected_email_from": "From: sender@example.org"
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_generate_status": False,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_output_dir_files": [],
            "expected_email_count": 1,
            "expected_email_subject": "Error processing digest file: ",
            "expected_email_from": "From: sender@example.org"
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_generate_status": False,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_output_dir_files": [],
            "expected_email_count": 1,
            "expected_email_subject": "Error processing digest file: ",
            "expected_email_from": "From: sender@example.org"
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_email_smtp_connect):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.temp_dir)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.activity_status, test_data.get("expected_activity_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.build_status, test_data.get("expected_build_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.generate_status, test_data.get("expected_generate_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.approve_status, test_data.get("expected_approve_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.email_status, test_data.get("expected_email_status"),
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
        # check for a docx file in the output_dir
        if test_data.get("expected_output_dir_files"):
            self.assertEqual(list_test_dir(self.activity.output_dir),
                             test_data.get("expected_output_dir_files"))
        # check email files and contents
        email_files_filter = os.path.join(self.activity.temp_dir, "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0], 'rb') as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(test_data.get("expected_email_subject") in first_email_content)
                if test_data.get("expected_email_from"):
                    self.assertTrue(test_data.get("expected_email_from") in first_email_content)


class TestEmailDigestFileName(unittest.TestCase):

    def test_output_file_name(self):
        "docx output file name with good input"
        digest_content = Digest()
        digest_content.author = 'Anonymous'
        digest_content.doi = '10.7554/eLife.99999'
        expected = 'Anonymous_99999.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)

    def test_output_file_name_unicode(self):
        "docx output file name with unicode author name"
        digest_content = Digest()
        digest_content.author = u'Nö'
        digest_content.doi = '10.7554/eLife.99999'
        expected = u'Nö_99999.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)

    def test_output_file_name_no_doi(self):
        "docx output file name when no doi attribute"
        digest_content = Digest()
        expected = 'None_0None.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)

    def test_output_file_name_bad_object(self):
        "docx output file name when digest is None"
        digest_content = None
        expected = None
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)


class TestEmailSubject(unittest.TestCase):

    def test_success_email_subject(self):
        "email subject line with correct, unicode data"
        digest_content = Digest()
        digest_content.author = u'Nö'
        digest_content.doi = '10.7554/eLife.99999'
        expected = u'Digest: Nö_99999'
        subject = activity_module.success_email_subject(digest_content)
        self.assertEqual(subject, expected)

    def test_success_email_subject_bad_object(self):
        "email subject line when digest is None"
        digest_content = None
        expected = None
        subject = activity_module.success_email_subject(digest_content)
        self.assertEqual(subject, expected)


if __name__ == '__main__':
    unittest.main()
