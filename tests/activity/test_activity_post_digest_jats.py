# coding=utf-8

import os
import unittest
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
import activity.activity_PostDigestJATS as activity_module
from activity.activity_PostDigestJATS import activity_PostDigestJATS as activity_object
from tests import read_fixture
import tests.activity.helpers as helpers
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse, fake_get_tmp_dir
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext
import provider.digest_provider as digest_provider


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
            "expected_post_status": None
        },
        {
            "comment": 'bad digest docx file example',
            "filename": 'DIGEST+99998.docx',
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_jats_status": None,
            "expected_post_status": None
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

    def test_do_activity_no_endpoint(self):
        "test returning True if the endpoint is not specified in the settings"
        del(settings_mock.typesetter_digest_endpoint)
        activity = activity_object(settings_mock, FakeLogger(), None, None, None)
        result = activity.do_activity()
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)

    def test_do_activity_blank_endpoint(self):
        "test returning True if the endpoint is blank"
        settings_mock.typesetter_digest_endpoint = ""
        activity = activity_object(settings_mock, FakeLogger(), None, None, None)
        result = activity.do_activity()
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)


class TestPostPayload(unittest.TestCase):

    def setUp(self):
        self.temp_dir = fake_get_tmp_dir()
        self.digest_config = digest_provider.digest_config(
            settings_mock.digest_config_section,
            settings_mock.digest_config_file)

    def tearDown(self):
        # clean the temporary directory
        helpers.delete_files_in_folder('tests/tmp', filter_out=['.keepme'])

    def test_post_payload(self):
        "POST payload for a digest"
        api_key = 'api_key'
        filename = os.path.join('tests', 'files_source', 'DIGEST 99999.docx')
        # JATS paragraphs are in an existing fixture file
        content = read_fixture('jats_content_99999.py', 'digests')
        expected = OrderedDict([
            ('apiKey', api_key),
            ('accountKey', 1),
            ('doi', '10.7554/eLife.99999'),
            ('type', 'digest'),
            ('content', content)
            ])
        build_status, digest = digest_provider.build_digest(
            filename, self.temp_dir, None, self.digest_config)
        # build the jats_content from the filename
        jats_content = digest_provider.digest_jats(digest)
        # build the payload for the POST
        payload = activity_module.post_payload(digest, jats_content, api_key)
        # make assertions
        self.assertEqual(payload, expected)

    def test_post_payload_no_digest(self):
        "POST payload for when there is no digest"
        digest = None
        jats_content = '<p>JATS content</p>'
        api_key = 'api_key'
        expected = None
        # build the payload for the POST
        payload = activity_module.post_payload(digest, jats_content, api_key)
        # make assertions
        self.assertEqual(payload, expected)


class TestPost(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_params(self, fake_connection):
        "test posting data as params only"
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = 'http://localhost/?type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        expected_body = None
        # populate the fake request
        resp = activity_module.post_as_params(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_data(self, fake_connection):
        "test posting data as data only"
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = 'http://localhost/'
        expected_body = 'type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        # populate the fake request
        resp = activity_module.post_as_data(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_json(self, fake_connection):
        "test posting data as data only"
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = 'http://localhost/'
        expected_body = '{"type": "digest", "content": "<p>\\"98%\\"\\u03b2</p>"}'
        # populate the fake request
        resp = activity_module.post_as_json(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)


if __name__ == '__main__':
    unittest.main()
