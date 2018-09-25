# coding=utf-8

import unittest
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
    ('stage', 'preview'),
    ('relatedContent', [
        OrderedDict([
            ('type', 'research-article'),
            ('status', 'vor'),
            ('id', '99999'),
            ])
        ])
    ])


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
            "comment": "set a digest as published",
            "article_id": '99999',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_stage": "published",
            "expected_approve_status": True,
            "expected_stage_status": True,
            "expected_put_status": True
        },
    )
    def test_do_activity(self, test_data, fake_emit, fake_get_digest, fake_put_digest):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        fake_get_digest.return_value = DIGEST_DATA
        fake_put_digest.return_value = None
        # do the activity
        result = self.activity.do_activity(ACTIVITY_DATA)
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
        self.assertEqual(self.activity.digest_content.get("stage"), test_data.get("expected_stage"))


if __name__ == '__main__':
    unittest.main()
