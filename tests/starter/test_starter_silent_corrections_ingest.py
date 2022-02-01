import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_SilentCorrectionsIngest import starter_SilentCorrectionsIngest
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger

RUN_EXAMPLE = u"1ee54f9a-cb28-4c8e-8232-4b317cf4beda"


class TestStarterSilentCorrectionsIngest(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_SilentCorrectionsIngest(settings_mock, self.fake_logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "SilentCorrectionsIngest_elife-00353-vor-r1.zip"),
                ("workflow_name", "SilentCorrectionsIngest"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                (
                    "input",
                    (
                        "{"
                        '"event_name": "ObjectCreated:Put",'
                        ' "event_time": "2016-07-28T16:14:27.809576Z",'
                        ' "bucket_name": "jen-elife-production-final",'
                        ' "file_name": "elife-00353-vor-r1.zip",'
                        ' "file_etag": "e7f639f63171c097d4761e2d2efe8dc4",'
                        ' "file_size": 1097506,'
                        ' "run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",'
                        ' "version_lookup_function": "article_highest_version",'
                        ' "run_type": "silent-correction",'
                        ' "force": true'
                        "}"
                    ),
                ),
            ]
        )
        params = self.starter.get_workflow_params(
            run=RUN_EXAMPLE,
            info=S3NotificationInfo.from_dict(test_data.silent_ingest_article_zip_data),
        )
        self.assertEqual(params, expected)

    def test_silent_corrections_ingest_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info={},
        )

    @patch("boto3.client")
    def test_silent_corrections_ingest_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.start(
            settings=settings_mock,
            run=RUN_EXAMPLE,
            info=S3NotificationInfo.from_dict(test_data.silent_ingest_article_zip_data),
        )
