# coding=utf-8

import unittest
from mock import patch
from ddt import ddt, data
import activity.activity_GenerateDecisionLetterJATS as activity_module
from activity.activity_GenerateDecisionLetterJATS import (
    activity_GenerateDecisionLetterJATS as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeSession, FakeStorageContext
import tests.activity.test_activity_data as test_activity_data
import tests.activity.helpers as helpers


def input_data(file_name_to_change=''):
    activity_data = test_case_data.ingest_decision_letter_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestGenerateDecisionLetterJATS(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        helpers.delete_files_in_folder(
            test_activity_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(activity_module, 'get_session')
    @patch.object(activity_module, 'storage_context')
    @patch.object(activity_module.download_helper, 'storage_context')
    @data(
        {
            "comment": 'decision letter zip file example',
            "filename": 'elife-39122.zip',
            "expected_result": True,
            "expected_doi_0": '10.7554/eLife.39122.sa1',
        },
    )
    def test_do_activity(self, test_data, fake_download_storage_context,
                         fake_storage_context, mock_session):
        activity_input_data = input_data(test_data.get("filename"))
        # copy XML files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()
        # activity storage context
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_dest_folder)
        # mock the session
        fake_session = FakeSession({})
        mock_session.return_value = fake_session
        # do the activity
        result = self.activity.do_activity(activity_input_data)
        filename_used = input_data(test_data.get("filename")).get("file_name")
        # check assertions
        self.assertEqual(
            result, test_data.get("expected_result"),
            ('failed in {comment}, got {result}, filename {filename}, ' +
             'input_file {input_file}').format(
                 comment=test_data.get("comment"),
                 result=result,
                 input_file=self.activity.input_file,
                 filename=filename_used))

        # check article values
        if test_data.get("expected_doi_0"):
            self.assertEqual(self.activity.articles[0].doi, test_data.get("expected_doi_0"),
                             'failed in {comment}'.format(comment=test_data.get("comment")))

        # check bucket XML resource value
        self.assertEqual(
            self.activity.xml_bucket_resource,
            's3://dev-elife-bot-decision-letter-output/elife39122/elife-39122.xml')

        # check session values
        self.assertEqual(fake_session.get_value('bucket_folder_name'), 'elife39122')
        self.assertEqual(fake_session.get_value('xml_file_name'), 'elife-39122.xml')

    @patch.object(FakeStorageContext, 'set_resource_from_string')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_module, 'storage_context')
    @patch.object(activity_module.download_helper, 'storage_context')
    def test_do_activity_exception(self, fake_download_storage_context,
                                   fake_storage_context, mock_session, fake_set_resource):
        activity_input_data = input_data('elife-39122.zip')
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_storage_context.return_value = FakeStorageContext()
        fake_session = FakeSession({})
        mock_session.return_value = fake_session
        # mock the exception
        fake_set_resource.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(activity_input_data)
        self.assertEqual(result, activity_object.ACTIVITY_PERMANENT_FAILURE)

        # check session values will be empty
        self.assertEqual(fake_session.get_value('bucket_folder_name'), None)
        self.assertEqual(fake_session.get_value('xml_file_name'), None)
