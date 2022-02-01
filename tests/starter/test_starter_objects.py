import unittest
from collections import OrderedDict
from mock import patch
import botocore
from starter.objects import Starter, default_workflow_params
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger


class TestStarterObjectInit(unittest.TestCase):
    def test_starter_init_no_logger(self):
        starter_object = Starter(settings_mock, name="Ping")
        self.assertIsNotNone(starter_object.logger)
        self.assertIsNotNone(starter_object.name)

    def test_starter_init_no_logger_no_name(self):
        starter_object = Starter(settings_mock)
        self.assertIsNotNone(starter_object.logger)


class TestStarterObject(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = Starter(settings_mock, self.logger)
        self.exception = botocore.exceptions.ClientError(
            {"Error": {"Code": "WorkflowExecutionAlreadyStartedFault"}},
            "operation_name",
        )

    @patch("boto3.client")
    def test_connect_to_swf(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.connect_to_swf()
        self.assertIsNotNone(self.starter.client)

    @patch("boto3.client")
    def test_start_workflow_execution(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        workflow_params = {}
        self.starter.start_workflow_execution(workflow_params)
        self.assertEqual(self.logger.loginfo[-1], "got response: \nnull")

    @patch.object(FakeSWFClient, "start_workflow_execution")
    @patch("boto3.client")
    def test_start_workflow_execution_exception(self, fake_client, fake_start):
        fake_client.return_value = FakeSWFClient()
        fake_start.side_effect = self.exception
        workflow_params = {}
        self.starter.start_workflow_execution(workflow_params)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "WorkflowExecutionAlreadyStartedFault: "
                "There is already a running workflow with ID None"
            ),
        )

    @patch("boto3.client")
    def test_start_swf_workflow_execution(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        workflow_params = {}
        self.starter.start_swf_workflow_execution(workflow_params)
        self.assertEqual(self.logger.loginfo[-1], "got response: \nnull")

    @patch.object(FakeSWFClient, "start_workflow_execution")
    @patch("boto3.client")
    def test_start_swf_workflow_execution_exception(self, fake_client, fake_start):
        fake_client.return_value = FakeSWFClient()
        fake_start.side_effect = self.exception
        workflow_params = {}

        with self.assertRaises(botocore.exceptions.ClientError):
            self.starter.start_swf_workflow_execution(workflow_params)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "WorkflowExecutionAlreadyStartedFault: "
                "There is already a running workflow with ID None"
            ),
        )

    @patch.object(FakeSWFClient, "start_workflow_execution")
    @patch("boto3.client")
    def test_start_swf_workflow_execution_unhandled_exception(
        self, fake_client, fake_start
    ):
        fake_client.return_value = FakeSWFClient()
        fake_start.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "UnknownResourceFault"}},
            "operation_name",
        )
        # also test some workflow parameters for increased test coverage
        workflow_params = {}
        workflow_params["task_list"] = "task_list"
        workflow_params["child_policy"] = "child_policy"
        workflow_params["execution_start_to_close_timeout"] = "300"
        workflow_params["input"] = "input"

        with self.assertRaises(botocore.exceptions.ClientError):
            self.starter.start_swf_workflow_execution(workflow_params)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "Unhandled botocore.exceptions.ClientError exception for workflow with ID None"
            ),
        )


class TestDefaultWorkflowParams(unittest.TestCase):
    def test_default_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", None),
                ("workflow_name", None),
                ("workflow_version", None),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                ("input", None),
            ]
        )
        params = default_workflow_params(settings_mock)
        self.assertEqual(params, expected)
