# coding=utf-8

import unittest
import copy
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
import activity.activity_CreateDigestMediumPost as activity_module
from activity.activity_CreateDigestMediumPost import (
    activity_CreateDigestMediumPost as activity_object)
import provider.article as article
import provider.lax_provider as lax_provider
import provider.digest_provider as digest_provider
import provider.article_processing as article_processing
from tests import read_fixture
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


ACTIVITY_DATA = {
    "run": "",
    "article_id": "99999",
    "version": "1",
    "status": "vor",
    "expanded_folder": "digests",
    "run_type": None
}


def digest_activity_data(data, status=None, run_type=None):
    new_data = copy.copy(data)
    if new_data and status:
        new_data["status"] = status
    if new_data and run_type:
        new_data["run_type"] = run_type
    return new_data


@ddt
class TestCreateDigestMediumPost(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch('digestparser.medium_post.post_content')
    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(article_processing, 'storage_context')
    @patch.object(article, 'storage_context')
    @patch.object(digest_provider, 'storage_context')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "approved for medium post",
            "bucket_resources": ["elife-15747-v2.xml"],
            "bot_bucket_resources": ["digests/outbox/99999/digest-99999.docx",
                                     "digests/outbox/99999/digest-99999.jpg"],
            "first_vor": True,
            "lax_highest_version": '1',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_medium_content": read_fixture('medium_content_99999.py', 'digests')
        },
        {
            "comment": "a digest with no image",
            "bucket_resources": ["elife-15747-v2.xml"],
            "bot_bucket_resources": ["digests/outbox/99999/digest-99999.docx"],
            "first_vor": True,
            "lax_highest_version": '1',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_medium_content": read_fixture('medium_content_99999_no_image.py', 'digests')
        },
        {
            "comment": "not first vor",
            "bucket_resources": ["elife-15747-v2.xml"],
            "bot_bucket_resources": ["digests/outbox/99999/digest-99999.docx",
                                     "digests/outbox/99999/digest-99999.jpg"],
            "first_vor": False,
            "lax_highest_version": '1',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_medium_content": None
        },
    )
    def test_do_activity(self, test_data, fake_emit, fake_storage_context,
                         fake_article_storage_context, fake_processing_storage_context,
                         fake_highest_version, fake_first, fake_post_content):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        activity_data = digest_activity_data(
            ACTIVITY_DATA
            )
        named_storage_context = FakeStorageContext()
        if test_data.get('bucket_resources'):
            named_storage_context.resources = test_data.get('bucket_resources')
        fake_article_storage_context.return_value = named_storage_context
        bot_storage_context = FakeStorageContext()
        if test_data.get('bot_bucket_resources'):
            bot_storage_context.resources = test_data.get('bot_bucket_resources')
        fake_storage_context.return_value = bot_storage_context
        fake_processing_storage_context.return_value = FakeStorageContext()
        # lax mocking
        fake_highest_version.return_value = test_data.get('lax_highest_version')
        fake_first.return_value = test_data.get("first_vor")
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        self.assertEqual(self.activity.medium_content, test_data.get("expected_medium_content"))

    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity_missing_credentials(self, fake_emit):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        activity_data = digest_activity_data(
            ACTIVITY_DATA
            )
        self.activity.digest_config['medium_application_client_id'] = ''
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)

    @patch.object(lax_provider, 'article_first_by_status')
    @patch.object(lax_provider, 'article_highest_version')
    @data(
        {
            "comment": "a poa",
            "article_id": '00000',
            "status": "poa",
            "version": 3,
            "run_type": None,
            "highest_version": '1',
            "first_vor": False,
            "expected": False
        },
        {
            "comment": "silent correction",
            "article_id": '00000',
            "status": "vor",
            "version": 3,
            "run_type": "silent-correction",
            "highest_version": '1',
            "first_vor": False,
            "expected": False
        },
        {
            "comment": "non-first vor",
            "article_id": '00000',
            "status": "vor",
            "version": 3,
            "run_type": None,
            "highest_version": '1',
            "first_vor": False,
            "expected": False
        },
    )
    def test_approve(self, test_data, fake_highest_version, fake_first):
        "test various scenarios for digest ingest approval"
        fake_highest_version.return_value = test_data.get("highest_version")
        fake_first.return_value = test_data.get("first_vor")
        status = self.activity.approve(
            test_data.get("article_id"),
            test_data.get("status"),
            test_data.get("version"),
            test_data.get("run_type")
        )
        self.assertEqual(status, test_data.get("expected"),
                         "failed in {comment}".format(comment=test_data.get("comment")))

    def test_create_medium_content_empty(self):
        result = activity_module.post_medium_content(None, {}, FakeLogger())
        self.assertIsNone(result)

    @patch('digestparser.medium_post.post_content')
    def test_create_medium_content_exception(self, fake_post_content):
        fake_post_content.side_effect = Exception("Something went wrong!")
        result = activity_module.post_medium_content('content', {}, FakeLogger())
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
