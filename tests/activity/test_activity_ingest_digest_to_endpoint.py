# coding=utf-8

import json
import copy
import unittest
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
from provider import article, article_processing, digest_provider, lax_provider
import activity.activity_IngestDigestToEndpoint as activity_module
from activity.activity_IngestDigestToEndpoint import (
    activity_IngestDigestToEndpoint as activity_object)
from tests import read_fixture
from tests.classes_mock import FakeSMTPServer
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext, FakeSession, FakeResponse
import tests.activity.test_activity_data as test_activity_data


def session_data(test_data):
    "return the session data for testing with values rewritten if specified"
    session_data = copy.copy(test_activity_data.session_example)
    for value in ['article_id', 'run_type', 'status', 'version', 'expanded_folder']:
        if test_data.get(value):
            session_data[value] = test_data.get(value)
    return session_data


IMAGE_JSON = {"width": 1, "height": 1}


RELATED_DATA = [{
    'id': '99999',
    'type': 'research-article',
    'status': 'vor',
    'version': 1,
    'doi': '10.7554/eLife.99999',
    'authorLine': 'Anonymous et al.',
    'title': 'A research article related to the digest',
    'stage': 'published',
    'published': '2018-06-04T00:00:00Z',
    'statusDate': '2018-06-04T00:00:00Z',
    'volume': 7,
    'elocationId': 'e99999'}]


@ddt
class TestIngestDigestToEndpointDoActivity(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch('activity.activity_IngestDigestToEndpoint.json_output.requests.get')
    @patch.object(article, 'storage_context')
    @patch.object(article_processing, 'storage_context')
    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(lax_provider, 'article_snippet')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(digest_provider, 'storage_context')
    @patch.object(digest_provider, 'put_digest')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "digest files with no existing digest json ingested",
            "bucket_resources": ["elife-15747-v2.xml"],
            "bot_bucket_resources": ["digests/outbox/99999/digest-99999.docx",
                                     "digests/outbox/99999/digest-99999.jpg"],
            "expanded_folder": "digests",
            "article_id": '99999',
            "first_vor": True,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_statuses": OrderedDict([
                ("approve", True),
                ("download", True),
                ("generate", True),
                ("ingest", True),
            ]),
            "expected_json_contains": [
                u'"title": "Fishing for errors in the\u00a0tests"',
                "Microbes live in us and on us",
                '"stage": "preview"',
                ],
            "expected_log_info": [
                'Digest stage value preview']
        },
        {
            "comment": "silent correction of current version",
            "article_id": '99999',
            "run_type": "silent-correction",
            "status": 'vor',
            'version': '1',
            "first_vor": True,
            "lax_highest_version": '1',
            "article_snippet": RELATED_DATA[0],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_statuses": OrderedDict([
                ("approve", True),
                ("download", True),
                ("generate", True),
                ("ingest", True),
            ]),
            "expected_log_info": [
                'Digest stage value published']
        },
    )
    def test_do_activity(self, test_data, fake_emit,
                         fake_session, fake_put_digest,
                         fake_provider_storage_context,
                         fake_highest_version, fake_article_snippet,
                         fake_first, fake_processing_storage_context,
                         fake_article_storage_context, fake_get):
        # copy files into the input directory using the storage context
        fake_emit.return_value = True
        named_storage_context = FakeStorageContext()
        if test_data.get('bucket_resources'):
            named_storage_context.resources = test_data.get('bucket_resources')
        fake_article_storage_context.return_value = named_storage_context
        bot_storage_context = FakeStorageContext()
        if test_data.get('bot_bucket_resources'):
            bot_storage_context.resources = test_data.get('bot_bucket_resources')
        fake_provider_storage_context.return_value = bot_storage_context
        fake_processing_storage_context.return_value = FakeStorageContext()
        fake_first.return_value = test_data.get("first_vor")
        session_test_data = session_data(test_data)
        fake_session.return_value = FakeSession(session_test_data)
        fake_put_digest.return_value = FakeResponse(204, None)
        fake_highest_version.return_value = test_data.get('lax_highest_version')
        fake_article_snippet.return_value = 200, test_data.get('article_snippet')

        fake_get.return_value = FakeResponse(200, IMAGE_JSON)
        activity_data = test_activity_data.data_example_before_publish
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses,
                         test_data.get("expected_statuses"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        if self.activity.digest_content and test_data.get("expected_json_contains"):
            json_string = json.dumps(self.activity.digest_content)
            for expected in test_data.get("expected_json_contains"):
                self.assertTrue(
                    (expected in json_string, 'failed in json_content in {comment}'.format(
                        comment=test_data.get("comment"))))
        if test_data.get('expected_log_info'):
            for loginfo in test_data.get('expected_log_info'):
                self.assertTrue(
                    loginfo in self.activity.logger.loginfo,
                    'failed in {comment}, "{loginfo}" not in loginfo'.format(
                        comment=test_data.get("comment"),
                        loginfo=loginfo))

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(lax_provider, 'article_highest_version')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "poa article has no digest",
            "article_id": '99999',
            "status": 'poa',
            'version': '1',
            "lax_highest_version": '1',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_statuses": OrderedDict([
                ("approve", False),
                ("download", None),
                ("generate", None),
                ("ingest", None),
            ]),
            "expected_log_info": [
                '\nNot ingesting digest for PoA article 99999',
                'Digest for article 99999 was not approved for ingestion']
        },
        {
            "comment": "silent correction of a previous version",
            "article_id": '99999',
            "run_type": "silent-correction",
            "status": 'vor',
            'version': '1',
            "first_vor": False,
            "lax_highest_version": '2',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_statuses": OrderedDict([
                ("approve", False),
                ("download", None),
                ("generate", None),
                ("ingest", None),
            ]),
            "expected_log_info": [
                ('\nNot ingesting digest for silent correction 99999 version 1'
                 ' is less than highest version 2'),
                'Digest for article 99999 was not approved for ingestion']
        },
        {
            "comment": "silent correction exception for bad version number",
            "article_id": '99999',
            "run_type": "silent-correction",
            "status": 'vor',
            "lax_highest_version": None,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_statuses": OrderedDict([
                ("approve", False),
                ("download", None),
                ("generate", None),
                ("ingest", None),
            ]),
            "expected_log_info": [
                'Digest for article 99999 was not approved for ingestion']
        },
    )
    def test_do_activity_approve_false(self, test_data, fake_emit,
                                       fake_session, fake_highest_version,
                                       fake_first, fake_email_smtp_connect):
        "situations where approve will be false"
        fake_emit.return_value = True
        fake_first.return_value = test_data.get("first_vor")
        session_test_data = session_data(test_data)
        fake_session.return_value = FakeSession(session_test_data)
        fake_highest_version.return_value = test_data.get('lax_highest_version')
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())

        activity_data = test_activity_data.data_example_before_publish
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses,
                         test_data.get("expected_statuses"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        if test_data.get('expected_log_info'):
            for loginfo in test_data.get('expected_log_info'):
                self.assertTrue(
                    loginfo in self.activity.logger.loginfo,
                    'failed in {comment}, "{loginfo}" not in loginfo'.format(
                        comment=test_data.get("comment"),
                        loginfo=loginfo))

    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(digest_provider, 'storage_context')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity_no_digest(self, fake_emit, fake_session, fake_provider_storage_context,
                                   fake_highest_version, fake_first):
        "article with no digest files"
        fake_emit.return_value = True
        fake_session.return_value = FakeSession({})
        fake_provider_storage_context.return_value = FakeStorageContext()
        fake_first.return_value = True
        session_test_data = session_data({})
        fake_session.return_value = FakeSession(session_test_data)
        fake_highest_version.return_value = 1
        activity_data = test_activity_data.data_example_before_publish

        # do the activity
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)
        self.assertEqual(self.activity.statuses.get("approve"), False)
        self.assertEqual(self.activity.statuses.get("download"), None)
        self.assertEqual(
            'Digest docx file does not exist in S3 for article 00353',
            self.activity.logger.loginfo[-2])
        self.assertEqual(
            'Digest for article 00353 was not approved for ingestion',
            self.activity.logger.loginfo[-1])

    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_bad_data(self, fake_session):
        "test bad data will be a permanent failure"
        fake_session.return_value = FakeSession({})
        activity_data = None
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)

    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_bad_queue(self, fake_session):
        "test a bad message queue by not mocking it"
        fake_session.return_value = FakeSession({})
        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_PERMANENT_FAILURE
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)

    @patch.object(digest_provider, 'docx_exists_in_s3')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_docx_exists_exception(self, fake_session, fake_emit, fake_first,
                                               fake_highest_version, fake_docx_exists):
        "test and error when checking if a docx exists"
        fake_emit.return_value = True
        fake_session.return_value = FakeSession({})
        fake_first.return_value = True
        fake_highest_version.return_value = 1
        session_test_data = session_data({})
        fake_session.return_value = FakeSession(session_test_data)
        fake_docx_exists.return_value = False
        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_SUCCESS
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch.object(digest_provider, 'download_docx_from_s3')
    @patch.object(digest_provider, 'storage_context')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_bad_download(self, fake_session, fake_storage_context, fake_download,
                                      fake_emit, fake_first, fake_highest_version,
                                      fake_email_smtp_connect):
        "test unable to download a digest docx file"
        fake_emit.return_value = True
        fake_session.return_value = FakeSession({})
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_first.return_value = True
        fake_highest_version.return_value = 1
        named_fake_storage_context = FakeStorageContext()
        named_fake_storage_context.resource_exists = lambda return_true: True
        fake_storage_context.return_value = named_fake_storage_context
        fake_download.return_value = None
        session_test_data = session_data({})
        fake_session.return_value = FakeSession(session_test_data)
        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_SUCCESS
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, 'related_from_lax')
    @patch.object(article_processing, 'download_article_xml')
    @patch.object(digest_provider, 'image_file_name_from_s3')
    @patch.object(digest_provider, 'download_docx_from_s3')
    @patch.object(activity_object, 'approve')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_lax_exception(
            self, fake_session, fake_emit, fake_email_smtp_connect,
            fake_approve, fake_download,
            fake_image, fake_download_article_xml, fake_related_from_lax):
        fake_emit.return_value = True
        session_test_data = session_data({})
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_session.return_value = FakeSession(session_test_data)
        fake_approve.return_value = True
        fake_download.return_value = True
        fake_image.return_value = True
        fake_download_article_xml.return_value = True
        fake_related_from_lax.side_effect = Exception('Related from lax exception')

        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_SUCCESS
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            ('Error in gathering digest details:'
             ' Failed to get related from lax for digest 00353 in Ingest Digest'
             ' to API endpoint: Related from lax exception'))

    @patch.object(activity_object, 'digest_json')
    @patch.object(activity_object, 'gather_digest_details')
    @patch.object(activity_object, 'approve')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_digest_json_exception(
            self, fake_session, fake_emit, fake_email_smtp_connect,
            fake_approve, fake_gather_digest_details, fake_digest_json):
        fake_emit.return_value = True
        session_test_data = session_data({})
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_session.return_value = FakeSession(session_test_data)
        fake_approve.return_value = True
        fake_gather_digest_details.return_value = {}
        fake_digest_json.side_effect = Exception('Digest content exception')

        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_SUCCESS
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            ('Error in generating digest content for article: Failed to generate digest json'
             ' for 00353 in Ingest Digest to API endpoint: Digest content exception'))

    @patch.object(digest_provider, 'put_digest')
    @patch.object(activity_object, 'generate_digest_content')
    @patch.object(activity_object, 'gather_digest_details')
    @patch.object(activity_object, 'approve')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch('activity.activity_IngestDigestToEndpoint.get_session')
    def test_do_activity_put_digest_exception(
            self, fake_session, fake_emit, fake_email_smtp_connect,
            fake_approve,
            fake_gather_digest_details, fake_generate_digest_content, fake_put_digest):
        fake_emit.return_value = True
        session_test_data = session_data({})
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_session.return_value = FakeSession(session_test_data)
        fake_approve.return_value = True
        fake_gather_digest_details.return_value = {}
        fake_generate_digest_content.return_value = {}
        fake_put_digest.side_effect = Exception('Put digest exception')

        activity_data = test_activity_data.data_example_before_publish
        expected_result = activity_object.ACTIVITY_SUCCESS
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            ('Failed to ingest digest json to endpoint 00353 in Ingest Digest to API endpoint:'
             ' Put digest exception'))


@ddt
class TestIngestDigestToEndpointDigestJson(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    @patch('activity.activity_IngestDigestToEndpoint.json_output.requests.get')
    @data(
        {
            "comment": "Minimal json output of digest only",
            "docx_file": "tests/files_source/digests/outbox/99999/digest-99999.docx",
            "image_file": None,
            "jats_file": None,
            "related": None,
            "expected_json_file": "json_content_99999_minimal.py"
        },
        {
            "comment": "Basic json output including an image file",
            "docx_file": "tests/files_source/digests/outbox/99999/digest-99999.docx",
            "image_file": "digest-99999.jpg",
            "jats_file": None,
            "related": None,
            "expected_json_file": "json_content_99999_basic.py"
        },
        {
            "comment": "JSON output with image file and JATS paragraph replacements",
            "docx_file": "tests/files_source/digests/outbox/99999/digest-99999.docx",
            "image_file": "digest-99999.jpg",
            "jats_file": "tests/test_data/elife-15747-v2.xml",
            "related": None,
            "expected_json_file": "json_content_99999_jats.py"
        },
        {
            "comment": "JSON output from all possible source data",
            "docx_file": "tests/files_source/digests/outbox/99999/digest-99999.docx",
            "image_file": "digest-99999.jpg",
            "jats_file": "tests/test_data/elife-15747-v2.xml",
            "related": RELATED_DATA,
            "expected_json_file": "json_content_99999_full.py"
        },
    )
    def test_digest_json(self, test_data, fake_get):
        "test producing digest json with various inputs"
        fake_get.return_value = FakeResponse(200, IMAGE_JSON)
        json_content = self.activity.digest_json(
            test_data.get("docx_file"),
            test_data.get("jats_file"),
            test_data.get("image_file"),
            test_data.get("related"),
        )
        folder_name = "digests"
        expected_json = read_fixture(test_data.get("expected_json_file"), folder_name)
        self.assertEqual(json_content, expected_json)


class TestIngestDigestToEndpointSession(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    def test_session_data_none_data(self):
        "test no data supplied"
        session_data = self.activity.session_data(None)
        self.assertEqual(session_data[0], None)

    def test_session_data_bad_data(self):
        "test missing data run attribute"
        session_data = self.activity.session_data({})
        self.assertEqual(session_data[0], None)


class TestIngestDigestToEndpointEmit(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    def test_emit_start_message_none_data(self):
        "test missing data run attribute"
        success = self.activity.emit_start_message(None, None, None)
        self.assertEqual(success, None)

    def test_emit_start_message_no_connection(self):
        "test a possible bad connection to the emit queue"
        success = self.activity.emit_start_message("", "", "")
        self.assertEqual(success, None)

    def test_activity_end_message_ingest(self):
        "activity end message after a digest ingest"
        article_id = "00353"
        statuses = {"ingest": True}
        expected = ("Finished ingest digest to endpoint for 00353. Statuses {'ingest': True}" +
                    " Preview link https://preview/digests/00353")
        message = self.activity.activity_end_message(article_id, statuses)
        self.assertEqual(message, expected)

    def test_activity_end_message_no_ingest(self):
        "activity end message after no digest ingested"
        article_id = "00353"
        statuses = {"ingest": None}
        expected = "No digest ingested for 00353. Statuses {'ingest': None}"
        message = self.activity.activity_end_message(article_id, statuses)
        self.assertEqual(message, expected)

    @patch.object(activity_object, 'emit_monitor_event')
    def test_emit_error_message(self, fake_emit):
        "test a possible bad connection to the emit queue"
        fake_emit.return_value = True
        success = self.activity.emit_error_message("", "", "", "")
        self.assertEqual(success, True)


class TestIngestDigestToEndpointPreview(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    def test_digest_preview_link(self):
        "digest preview url from settings value and article_id"
        article_id = "00353"
        expected = "https://preview/digests/" + article_id
        preview_link = self.activity.digest_preview_link(article_id)
        self.assertEqual(preview_link, expected)


@ddt
class TestIngestDigestToEndpointApprove(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.logger, None, None, None)

    @patch.object(digest_provider, 'docx_exists_in_s3')
    @patch.object(lax_provider, 'article_status_version_map')
    @patch.object(lax_provider, 'article_highest_version')
    @data(
        {
            "comment": "normal first vor",
            "article_id": '00000',
            "status": "vor",
            "version": 2,
            "run_type": None,
            "highest_version": "2",
            "version_map": {"poa": [1], "vor": [2]},
            "expected": True
        },
        {
            "comment": "poa is not approved",
            "article_id": '00000',
            "status": "poa",
            "version": 2,
            "run_type": None,
            "highest_version": "2",
            "version_map": {"poa": [1]},
            "expected": False
        },
        {
            "comment": "silent correction of highest vor",
            "article_id": '00000',
            "status": "vor",
            "version": 3,
            "run_type": "silent-correction",
            "highest_version": "3",
            "version_map": {"poa": [1], "vor": [2, 3]},
            "expected": True
        },
        {
            "comment": "silent correction of older version of vor",
            "article_id": '00000',
            "status": "vor",
            "version": 2,
            "run_type": "silent-correction",
            "highest_version": "3",
            "version_map": {"poa": [1], "vor": [2, 3]},
            "expected": False
        },
        {
            "comment": "ingest a non-first vor",
            "article_id": '00000',
            "status": "vor",
            "version": 3,
            "run_type": None,
            "highest_version": "3",
            "version_map": {"poa": [1], "vor": [2, 3]},
            "expected": False
        },
        )
    def test_approve(self, test_data, fake_highest_version, fake_version_map, fake_doc_exists):
        "test various scenarios for digest ingest approval"
        fake_doc_exists.return_value = True
        fake_highest_version.return_value = test_data.get("highest_version")
        fake_version_map.return_value = test_data.get("version_map")
        status = self.activity.approve(
            test_data.get("article_id"),
            test_data.get("status"),
            test_data.get("version"),
            test_data.get("run_type")
        )
        self.assertEqual(status, test_data.get("expected"),
                         "failed in {comment}".format(comment=test_data.get("comment")))


if __name__ == '__main__':
    unittest.main()
