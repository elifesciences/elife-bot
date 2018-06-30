import unittest
import activity.activity_EmailDigest as activity_module
from activity.activity_EmailDigest import activity_EmailDigest as activity_object
from mock import patch
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from provider.simpleDB import SimpleDB
import tests.test_data as test_case_data
import os
from ddt import ddt, data
from tests.activity.classes_mock import FakeStorageContext
from digestparser.objects import Digest


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
        self.activity.clean_tmp_dir()

    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
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
            "expected_output_dir_files": ['Digest 99999.docx']
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST 99999.zip',
            "expected_result": True,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_generate_status": True,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_digest_image_file": u'IMAGE 99999.jpeg',
            "expected_output_dir_files": ['Digest 99999.docx']
        },
        {
            "comment": 'digest bad file example',
            "filename": '',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_generate_status": False,
            "expected_approve_status": True,
            "expected_email_status": True,
            "expected_output_dir_files": []
        },
    )
    def test_do_activity(self, test_data, fake_storage_context,
                         fake_add_email):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
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
        if (self.activity.digest and self.activity.digest.image and
            test_data.get("expected_digest_image_file")):
            file_name = self.activity.digest.image.file.split(os.sep)[-1]
            self.assertEqual(file_name, test_data.get("expected_digest_image_file"),
                             'failed in {comment}'.format(comment=test_data.get("comment")))
        # check for a docx file in the output_dir
        if test_data.get("expected_output_dir_files"):
            self.assertEqual(list_test_dir(self.activity.output_dir),
                             test_data.get("expected_output_dir_files"))


class TestEmailDigestFileName(unittest.TestCase):

    def test_output_file_name(self):
        "docx output file name with good input"
        digest_content = Digest()
        digest_content.doi = '10.7554/eLife.99999'
        expected = 'Digest 99999.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)

    def test_output_file_name_no_doi(self):
        "docx output file name with good input"
        digest_content = Digest()
        expected = 'Digest 0None.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)

    def test_output_file_name_bad_object(self):
        "docx output file name with good input"
        digest_content = None
        expected = 'Digest 0None.docx'
        file_name = activity_module.output_file_name(digest_content)
        self.assertEqual(file_name, expected)


if __name__ == '__main__':
    unittest.main()
