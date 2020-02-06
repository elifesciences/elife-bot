# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
from provider import download_helper
from activity.activity_DepositDecisionLetterIngestAssets import (
    activity_DepositDecisionLetterIngestAssets as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


def input_data(file_name_to_change=''):
    activity_data = test_case_data.ingest_decision_letter_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestDepositDecisionLetterIngestAssets(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(testdata.ExpandArticle_files_dest_folder,
                                       filter_out=['.gitkeep'])

    @patch.object(download_helper, 'storage_context')
    @patch('activity.activity_DepositDecisionLetterIngestAssets.storage_context')
    @data(
        {
            "comment": 'decision letter zip file example',
            "filename": 'elife-39122.zip',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_asset_file_names": ['elife-39122-sa2-fig1.jpg', 'elife-39122-sa2-fig2.jpg'],
            "expected_file_list": ['elife-39122-sa2-fig1.jpg', 'elife-39122-sa2-fig2.jpg'],
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_download_storage_context):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # check asset file name values
        if self.activity.asset_file_names:
            asset_file_names = [
                file_name.split(os.sep)[-1] for file_name in self.activity.asset_file_names]
        self.assertEqual(sorted(asset_file_names), test_data.get("expected_asset_file_names"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))

        # Check destination folder as a list
        files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        compare_files = [file_name for file_name in files if file_name != '.gitkeep']
        self.assertEqual(compare_files, test_data.get("expected_file_list"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))


if __name__ == '__main__':
    unittest.main()
