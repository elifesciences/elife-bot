import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_LensArticlePublish import starter_LensArticlePublish
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger


class TestStarterLensArticlePublish(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_LensArticlePublish(settings_mock, self.logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "LensArticlePublish_666"),
                ("workflow_name", "LensArticlePublish"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", "1800"),
                ("input", '{"article_id": "00666"}'),
            ]
        )
        params = self.starter.get_workflow_params(doi_id="666")

        self.assertEqual(params, expected)

    def test_get_workflow_params_no_doi_id(self):
        with self.assertRaises(NullRequiredDataException) as test_exception:
            self.starter.get_workflow_params()
        self.assertEqual(
            str(test_exception.exception),
            "Did not get doi_id in starter LensArticlePublish",
        )

    @patch("boto3.client")
    def test_start(self, fake_client):
        doi_id = 3
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(self.starter.start(settings_mock, doi_id))
