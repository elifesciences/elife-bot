# coding=utf-8

import unittest
from mock import patch
from ddt import ddt, data
import activity.activity_PostDigestJATS as activity_module
from activity.activity_PostDigestJATS import activity_PostDigestJATS as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext


def input_data(file_name_to_change=''):
    activity_data = test_case_data.ingest_digest_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestPostDigestJats(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch('requests.post')
    @patch.object(activity_module.digest_provider, 'storage_context')
    @data(
        {
            "comment": 'digest docx file example',
            "filename": 'DIGEST+99999.docx',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999'
        },
        {
            "comment": 'digest zip file example',
            "filename": 'DIGEST+99999.zip',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999'
        },
        {
            "comment": 'digest file does not exist example',
            "filename": '',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_jats_status": None,
            "expected_post_status": True
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_jats_status": None,
            "expected_post_status": True
        },
        {
            "comment": 'digest author name encoding file example',
            "filename": 'DIGEST+99997.docx',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99997',
        },
        {
            "comment": 'digest bad post response',
            "filename": 'DIGEST+99999.docx',
            "post_status_code": 500,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": False,
            "expected_digest_doi": u'https://doi.org/10.7554/eLife.99999'
        },
    )
    def test_do_activity(self, test_data, fake_storage_context, post_mock):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        # POST response
        post_mock.return_value = FakeResponse(test_data.get("post_status_code"), None)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         ('failed in {comment}, got {result}, filename {filename}, ' +
                          'input_file {input_file}, digest {digest}').format(
                              comment=test_data.get("comment"),
                              result=result,
                              input_file=self.activity.input_file,
                              filename=filename_used,
                              digest=self.activity.digest))
        self.assertEqual(self.activity.statuses.get("build"),
                         test_data.get("expected_build_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("jats"),
                         test_data.get("expected_jats_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("post"),
                         test_data.get("expected_post_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # check digest values
        if self.activity.digest and test_data.get("expected_digest_doi"):
            self.assertEqual(self.activity.digest.doi, test_data.get("expected_digest_doi"),
                             'failed in {comment}'.format(comment=test_data.get("comment")))


if __name__ == '__main__':
    unittest.main()
