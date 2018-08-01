# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
import provider.digest_provider as digest_provider
from activity.activity_DepositDigestIngestAssets import (
    activity_DepositDigestIngestAssets as activity_object)
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
class TestDepositDigestIngestAssets(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(testdata.ExpandArticle_files_dest_folder, filter_out=['.gitkeep'])

    @patch.object(digest_provider, 'storage_context')
    @patch('activity.activity_DepositDigestIngestAssets.storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": None,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_file_list": []
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999',
            "expected_digest_image_file": u'IMAGE 99999.jpeg',
            "expected_dest_resource": 's3://ppd_cdn_bucket/digests/99999/IMAGE 99999.jpeg',
            "expected_file_list": [u'IMAGE 99999.jpeg']
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
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

        # Check the S3 object destination resource
        if 'expected_dest_resource' in test_data:
            self.assertEqual(self.activity.dest_resource, test_data.get("expected_dest_resource"))

        # Check destination folder as a list
        if 'expected_file_list' in test_data:
            files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
            compare_files = [file for file in files if file != '.gitkeep']
            self.assertEqual(compare_files, test_data.get("expected_file_list"))


if __name__ == '__main__':
    unittest.main()
