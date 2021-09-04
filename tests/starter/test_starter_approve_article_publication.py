import unittest
import json
from collections import OrderedDict
from mock import patch
from starter.starter_ApproveArticlePublication import starter_ApproveArticlePublication
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeBotoConnection
import tests.settings_mock as settings_mock
import tests.test_data as test_data


class TestStarterApproveArticlePublication(unittest.TestCase):
    def setUp(self):
        self.starter = starter_ApproveArticlePublication()

    def test_process_approve_article_publication(self):
        invalid_data = test_data.ApprovePublication_data()
        invalid_data["version"] = None
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            **invalid_data
        )

    @patch("boto.swf.layer1.Layer1")
    def test_approve_article_publication_starter(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.starter.start(
            settings=settings_mock, **test_data.ApprovePublication_data()
        )


class TestStarterApproveArticlePublicationWorkflowParams(unittest.TestCase):
    def setUp(self):
        # instantiate the starter object with settings in order to test get_workflow_params
        self.starter = starter_ApproveArticlePublication(settings_mock)

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
        workflow_data = self.starter.get_workflow_params(workflow=workflow, **data)
        self.assertEqual(workflow_data, expected)

    def test_get_workflow_params_no_workflow(self):
        invalid_data = test_data.ApprovePublication_data()
        self.assertRaises(
            NullRequiredDataException,
            self.starter.get_workflow_params,
            **invalid_data
        )
