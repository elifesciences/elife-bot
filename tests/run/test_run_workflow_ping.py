import datetime
import os
import unittest
from mock import patch
from moto import mock_swf
from botocore.config import Config
import boto3
from tests import settings_mock
from tests.classes_mock import FakeFlag
from tests.activity.classes_mock import FakeLogger
import decider
import worker
from starter.starter_Ping import starter_Ping as starter_class
from workflow.workflow_Ping import workflow_Ping as workflow_class
from provider import utils

class TestRunWorkflowPing(unittest.TestCase):
    @mock_swf
    def setUp(self):
        utils.set_envvar("MOTO_ALLOW_NONEXISTENT_REGION", "true")

        self.test_client = boto3.client(
            "swf",
            aws_access_key_id=settings_mock.aws_access_key_id,
            aws_secret_access_key=settings_mock.aws_secret_access_key,
            region_name=settings_mock.swf_region,
            config=Config(connect_timeout=50, read_timeout=70),
        )

    @patch("decider.create_log")
    @patch("worker.create_log")
    @mock_swf
    def test_run(self, fake_worker_log, fake_decider_log):
        "test running an SWF workflow execution using moto"
        # get the workflow name and steps
        workflow_object = workflow_class(settings=settings_mock, logger=None)
        workflow_type = workflow_object.definition.get("name")
        workflow_steps = workflow_object.definition.get("steps")

        # register the SWF domain
        self.test_client.register_domain(
            name=settings_mock.domain, workflowExecutionRetentionPeriodInDays="90"
        )

        # register the workflow type
        self.test_client.register_workflow_type(
            domain=settings_mock.domain,
            name=workflow_type,
            version="1",
            defaultExecutionStartToCloseTimeout="60",
            defaultTaskStartToCloseTimeout="60",
            defaultChildPolicy="TERMINATE",
        )

        # register the activity types
        for activity_type in {step.get("activity_type") for step in workflow_steps}:
            self.test_client.register_activity_type(
                domain=settings_mock.domain,
                name=activity_type,
                version="1",
                defaultTaskStartToCloseTimeout="60",
            )

        # start a workflow execution
        starter_logger = FakeLogger()
        starter_object = starter_class(settings_mock, starter_logger)
        starter_object.start_workflow()

        # worker and decider loggers
        worker_logger = FakeLogger()
        fake_worker_log.return_value = worker_logger
        decider_logger = FakeLogger()
        fake_decider_log.return_value = decider_logger

        # execute the workflow steps
        for step in range(len(workflow_steps)):
            # invoke decider
            decider.decide(settings_mock, FakeFlag())

            # invoke worker
            worker.work(settings_mock, FakeFlag())

        # final workflow decision
        decider.decide(settings_mock, FakeFlag())

        # assertions
        executions_response = self.test_client.list_closed_workflow_executions(
            domain=settings_mock.domain,
            startTimeFilter={
                "oldestDate": (
                    datetime.datetime.utcnow() - datetime.timedelta(days=365)
                ),
                "latestDate": (
                    datetime.datetime.utcnow() + datetime.timedelta(days=365)
                ),
            },
        )
        self.assertEqual(len(executions_response.get("executionInfos")), 1)

        message_count = str(worker_logger.loginfo).count(
            "respond_activity_task_completed returned"
        )
        self.assertEqual(message_count, len(workflow_steps))
