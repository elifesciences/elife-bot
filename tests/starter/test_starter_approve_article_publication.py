import unittest
import json
from collections import OrderedDict
from mock import patch
from starter.starter_ApproveArticlePublication import starter_ApproveArticlePublication
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeSWFClient
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.activity.classes_mock import FakeLogger


class TestStarterApproveArticlePublication(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = starter_ApproveArticlePublication(
            settings_mock, self.fake_logger
        )

    def test_get_workflow_params(self):
        data = test_data.ApprovePublication_data()
        workflow = "ApproveArticlePublication"
        expected = OrderedDict(
            [
                ("domain", settings_mock.domain),
                ("task_list", settings_mock.default_task_list),
                ("workflow_id", "%s_%s" % (workflow, data.get("article_id"))),
                ("workflow_name", workflow),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                (
                    "input",
                    json.dumps(data),
                ),
            ]
        )
        workflow_data = self.starter.get_workflow_params(**data)
        self.assertEqual(workflow_data, expected)

    def test_get_workflow_params_no_article_id(self):
        invalid_data = {}
        self.assertRaises(
            NullRequiredDataException, self.starter.get_workflow_params, **invalid_data
        )

    def test_process_approve_article_publication(self):
        invalid_data = test_data.ApprovePublication_data()
        invalid_data["version"] = None
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            **invalid_data
        )

    @patch("boto3.client")
    def test_approve_article_publication_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.start(
            settings=settings_mock, **test_data.ApprovePublication_data()
        )
