# coding=utf-8

import unittest
import copy
import requests
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
import provider.digest_provider as digest_provider
from activity.activity_PublishDigest import activity_PublishDigest as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse
import tests.test_data as shared_test_data


ACTIVITY_DATA = {
    "run": "",
    "article_id": "99999",
    "version": "1",
    "status": "vor",
    "expanded_folder": "",
}


DIGEST_DATA = OrderedDict([
    ('id', '99999'),
    ('title', 'Test'),
    ('published', '2016-06-16T00:00:00Z'),
    ('relatedContent', [
        OrderedDict([
            ('type', 'research-article'),
            ('status', 'vor'),
            ('id', '99999'),
            ])
        ])
    ])


def digest_data_no_published():
    "digest data with published removed"
    data = copy.copy(DIGEST_DATA)
    del(data["published"])
    return data


def digest_activity_data(data, status):
    new_data = copy.copy(data)
    if new_data and status:
        new_data["status"] = status
    return new_data


def digest_get_data(data, stage):
    new_data = copy.copy(data)
    if new_data and stage:
        new_data["stage"] = stage
    return new_data


@ddt
class TestPublishDigest(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch('provider.lax_provider.article_versions')
    @patch.object(requests, 'put')
    @patch.object(digest_provider, 'get_digest_preview')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "set a preview digest as published",
            "article_id": "99999",
            "status": "vor",
            "existing_digest_json": digest_data_no_published(),
            "put_response": FakeResponse(204, None),
            "stage": "preview",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_stage": "published",
            "expected_approve_status": True,
            "expected_put_status": True,
            "expected_published_date": "2015-12-29T00:00:00Z"
        },
        {
            "comment": "published digest with no date, put it to the endpoint",
            "article_id": "99999",
            "status": "vor",
            "existing_digest_json": digest_data_no_published(),
            "put_response": FakeResponse(204, None),
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_stage": "published",
            "expected_approve_status": True,
            "expected_put_status": True,
            "expected_published_date": "2015-12-29T00:00:00Z"
        },
        {
            "comment": "fail to put a digest",
            "article_id": "99999",
            "status": "vor",
            "existing_digest_json": DIGEST_DATA,
            "put_response": FakeResponse(500, None),
            "stage": "preview",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_stage": "published",
            "expected_approve_status": True,
            "expected_put_status": None,
            "expected_published_date": "2016-06-16T00:00:00Z"
        },
        {
            "comment": "an already published digest",
            "article_id": '99999',
            "existing_digest_json": DIGEST_DATA,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": True,
            "expected_put_status": None,
        },
        {
            "comment": "a poa article is not approved",
            "article_id": '99999',
            "status": "poa",
            "existing_digest_json": DIGEST_DATA,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": False,
            "expected_put_status": None,
        },
        {
            "comment": "no digest to publish",
            "article_id": '99999',
            "existing_digest_json": None,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": True,
            "expected_put_status": None
        },
    )
    def test_do_activity(self, test_data, fake_emit, fake_get_digest,
                         fake_put_digest, fake_article_versions):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        fake_get_digest.return_value = digest_get_data(
            test_data.get("existing_digest_json"),
            test_data.get("stage")
            )
        fake_put_digest.return_value = test_data.get("put_response")
        activity_data = digest_activity_data(
            ACTIVITY_DATA,
            test_data.get("status")
            )
        fake_article_versions.return_value = (
            200, shared_test_data.lax_article_versions_response_data)
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("approve"),
                         test_data.get("expected_approve_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("put"),
                         test_data.get("expected_put_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # check stage value in json_content
        if test_data.get("expected_stage"):
            self.assertEqual(self.activity.digest_content.get("stage"),
                             test_data.get("expected_stage"))
        # check published value in json_content
        if test_data.get("expected_published_date"):
            self.assertEqual(self.activity.digest_content.get("published"),
                             test_data.get("expected_published_date"))


if __name__ == '__main__':
    unittest.main()
