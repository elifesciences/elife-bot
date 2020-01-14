# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
from digestparser.objects import Digest
from provider import digest_provider, download_helper
from activity.activity_CopyDigestToOutbox import activity_CopyDigestToOutbox as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.test_data as test_case_data
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


def input_data(file_name_to_change=None):
    activity_data = test_case_data.ingest_digest_data
    if file_name_to_change is not None:
        activity_data["file_name"] = file_name_to_change
    return activity_data


def populate_outbox(resources):
    "populate the bucket with outbox files to later be deleted"
    for resource in resources:
        file_name = resource.split('/')[-1]
        file_path = testdata.ExpandArticle_files_dest_folder + '/' + file_name
        with open(file_path, 'a'):
            os.utime(file_path, None)


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

    @patch.object(download_helper, 'storage_context')
    @patch.object(digest_provider, 'storage_context')
    @patch('activity.activity_CopyDigestToOutbox.storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": 'DIGEST+99999.docx',
            "bucket_resources": ['s3://bucket/DIGEST 99999_alternate.docx'],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_file_list": ['digest-99999.docx']
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "bucket_resources": ['s3://bucket/IMAGE 99999.jpg',
                                 's3://bucket/DIGEST 99999_old.docx'],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_file_list": [ 'digest-99999.docx', 'digest-99999.jpeg']
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "bucket_resources": [],
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": []
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "bucket_resources": [],
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": []
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_provider_storage_context,
                         fake_download_storage_context):
        # copy files into the input directory using the storage context
        named_fake_storage_context = FakeStorageContext()
        named_fake_storage_context.resources = test_data.get('bucket_resources')
        fake_storage_context.return_value = named_fake_storage_context
        fake_provider_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        # populate the fake resources
        populate_outbox(test_data.get('bucket_resources'))
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


if __name__ == '__main__':
    unittest.main()
