# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
from digestparser.objects import Digest
import provider.digest_provider as digest_provider
from activity.activity_CopyDigestToOutbox import activity_CopyDigestToOutbox as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


def input_data(file_name_to_change=None):
    activity_data = test_case_data.ingest_digest_data
    if file_name_to_change is not None:
        activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestCopyDigestToOutbox(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(testdata.ExpandArticle_files_dest_folder,
                                       filter_out=['.gitkeep'])

    @patch.object(digest_provider, 'storage_context')
    @patch('activity.activity_CopyDigestToOutbox.storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": 'DIGEST+99999.docx',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_file_list": ['DIGEST 99999.docx']
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_file_list": ['DIGEST 99999.docx', 'IMAGE 99999.jpeg']
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "expected_digest_doi": None,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": []
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "expected_digest_doi": None,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": []
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_provider_storage_context):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        fake_provider_storage_context.return_value = FakeStorageContext()
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))

        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # Check destination folder as a list
        files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        compare_files = [file_name for file_name in files if file_name != '.gitkeep']
        self.assertEqual(compare_files, test_data.get("expected_file_list"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))

    def test_dest_resource_path(self):
        "test building the path to the bucket folder"
        digest = Digest()
        digest.doi = '10.7554/eLife.99999'
        bucket_name = 'elife-bot'
        expected = 's3://elife-bot/digests/outbox/99999/'
        resource_path = self.activity.dest_resource_path(digest, bucket_name)
        self.assertEqual(resource_path, expected)

    def test_file_dest_resource(self):
        "test the bucket destination resource path for a file"
        digest = Digest()
        digest.doi = '10.7554/eLife.99999'
        bucket_name = 'elife-bot'
        # create a full path to test stripping out folder names
        file_path = os.getcwd() + os.sep + 'DIGEST 99999.docx'
        expected = 's3://elife-bot/digests/outbox/99999/DIGEST 99999.docx'
        dest_resource = self.activity.file_dest_resource(digest, bucket_name, file_path)
        self.assertEqual(dest_resource, expected)


if __name__ == '__main__':
    unittest.main()
