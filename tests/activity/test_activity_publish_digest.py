# coding=utf-8

import unittest
import copy
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
import provider.digest_provider as digest_provider
from activity.activity_PublishDigest import activity_PublishDigest as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


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

    @patch.object(digest_provider, 'put_digest')
    @patch.object(digest_provider, 'get_digest')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "set a preview digest as published",
            "article_id": "99999",
            "status": "vor",
            "existing_digest_json": DIGEST_DATA,
            "stage": "preview",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_stage": "published",
            "expected_approve_status": True,
            "expected_stage_status": True,
            "expected_put_status": True
        },
        {
            "comment": "an already published digest",
            "article_id": '99999',
            "existing_digest_json": DIGEST_DATA,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": True,
            "expected_stage_status": None,
            "expected_put_status": None
        },
        {
            "comment": "a poa article is not approved",
            "article_id": '99999',
            "status": "poa",
            "existing_digest_json": DIGEST_DATA,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": False,
            "expected_stage_status": None,
            "expected_put_status": None
        },
        {
            "comment": "no digest to publish",
            "article_id": '99999',
            "existing_digest_json": None,
            "stage": "published",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_approve_status": True,
            "expected_stage_status": None,
            "expected_put_status": None
        },
    )
    def test_do_activity(self, test_data, fake_emit, fake_get_digest, fake_put_digest):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        fake_get_digest.return_value = digest_get_data(
            test_data.get("existing_digest_json"),
            test_data.get("stage")
            )
        fake_put_digest.return_value = None
        activity_data = digest_activity_data(
            ACTIVITY_DATA,
            test_data.get("status")
            )
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("approve"),
                         test_data.get("expected_approve_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("stage"),
                         test_data.get("expected_stage_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.statuses.get("put"),
                         test_data.get("expected_put_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # check stage value in json_content
        if self.activity.digest_content:
            self.assertEqual(self.activity.digest_content.get("stage"),
                             test_data.get("expected_stage"))


if __name__ == '__main__':
    unittest.main()
