import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_FTPArticle import starter_FTPArticle
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock


class TestStarterFTPArticle(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_FTPArticle(settings_mock, self.logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "FTPArticle_HEFCE_666"),
                ("workflow_name", "FTPArticle"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", "82800"),
                ("input", '{"data": {"workflow": "HEFCE", "elife_id": "666"}}'),
            ]
        )
        params = self.starter.get_workflow_params(workflow="HEFCE", doi_id="666")
        self.assertEqual(params, expected)

    def test_get_workflow_params_no_workflow(self):
        with self.assertRaises(NullRequiredDataException) as test_exception:
            self.starter.get_workflow_params()
        self.assertEqual(
            str(test_exception.exception), "Did not get a workflow argument. Required."
        )

    def test_get_workflow_params_unknown_workflow(self):
        with self.assertRaises(NullRequiredDataException) as test_exception:
            self.starter.get_workflow_params(workflow="Foo")
        self.assertEqual(
            str(test_exception.exception),
            "Value of workflow not found in supported WORKFLOW_NAMES.",
        )
        self.assertRaises(
            NullRequiredDataException,
            self.starter.get_workflow_params,
        )

    def test_get_workflow_params_no_doi_id(self):
        with self.assertRaises(NullRequiredDataException) as test_exception:
            self.starter.get_workflow_params(workflow="HEFCE")
        self.assertEqual(
            str(test_exception.exception), "Did not get a doi_id argument. Required."
        )

    @patch("boto3.client")
    def test_start(self, fake_client):
        workflow = "HEFCE"
        doi_id = 3
        fake_client.return_value = FakeSWFClient()
        self.assertIsNone(self.starter.start(settings_mock, workflow, doi_id))
