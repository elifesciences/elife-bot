import unittest
import json
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
from workflow.objects import Workflow


def decisions_data():
    with open("tests/test_data/decision.json", "r") as open_file:
        return json.loads(open_file.read())


PING_STEP = {
    "activity_type": "PingWorker",
    "activity_id": "PingWorker",
    "version": "1",
    "input": None,
    "control": None,
    "heartbeat_timeout": 300,
    "schedule_to_close_timeout": 300,
    "schedule_to_start_timeout": 300,
    "start_to_close_timeout": 300,
}


NEXT_STEP = {
    "activity_type": "NextStep",
    "activity_id": "NextStep",
    "version": "1",
    "input": None,
    "control": None,
    "heartbeat_timeout": 300,
    "schedule_to_close_timeout": 300,
    "schedule_to_start_timeout": 300,
    "start_to_close_timeout": 300,
}


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        logger = FakeLogger()
        conn = FakeLayer1()
        self.workflow = Workflow(settings_mock, logger, conn, None, None, None)

    def test_init(self):
        self.assertIsNone(self.workflow.name)
        self.assertIsNone(self.workflow.get_definition())

    def test_init_definition(self):
        "test __init__ coverage for conditional cases"
        settings = None
        logger = None
        workflow_definition = {"name": "WorkflowName"}
        workflow_object = Workflow(
            settings, logger, None, None, None, None, workflow_definition
        )
        self.assertEqual(workflow_object.get_definition(), workflow_definition)
        self.assertIsNone(workflow_object.domain)
        self.assertIsNone(workflow_object.task_list)

    def test_complete_workflow(self):
        self.assertIsNone(self.workflow.complete_workflow())

    def test_get_next_activities_single(self):
        "next activities for single step"
        workflow_definition = {"name": "WorkflowName", "steps": [PING_STEP, NEXT_STEP]}
        workflow_object = Workflow(
            settings_mock, None, None, None, decisions_data(), None, workflow_definition
        )
        next_activities = workflow_object.get_next_activities()
        self.assertEqual(len(next_activities), 1)
        self.assertEqual(next_activities[0]["activity_id"], "NextStep")

    def test_get_next_activities_parallel(self):
        "next activities for parallel steps"
        workflow_definition = {
            "name": "WorkflowName",
            "steps": [PING_STEP, [NEXT_STEP, NEXT_STEP]],
        }
        workflow_object = Workflow(
            settings_mock, None, None, None, decisions_data(), None, workflow_definition
        )
        next_activities = workflow_object.get_next_activities()
        self.assertEqual(len(next_activities), 2)
        self.assertEqual(next_activities[0]["activity_id"], "NextStep")
        self.assertEqual(next_activities[1]["activity_id"], "NextStep")

    def test_schedule_activity(self):
        next_activity = PING_STEP
        workflow_definition = {"name": "Ping", "task_list": "default"}
        self.workflow.load_definition(workflow_definition)
        decisions = self.workflow.schedule_activity(next_activity)
        first_decision_type = decisions._data[0].get("decisionType")
        first_decision_attrs = decisions._data[0].get(
            "scheduleActivityTaskDecisionAttributes"
        )
        self.assertEqual(first_decision_type, "ScheduleActivityTask")
        self.assertEqual(first_decision_attrs.get("activityId"), "PingWorker")

    def test_get_time(self):
        self.assertIsNotNone(self.workflow.get_time())

    def test_activity_status(self):
        "a few calls to activity_status for coverage"
        decisions = decisions_data()
        return_value = self.workflow.activity_status(decisions, None, None)
        self.assertFalse(return_value)
        return_value = self.workflow.activity_status(
            decisions, "PingWorker", "PingWorker"
        )
        self.assertTrue(return_value)
        return_value = self.workflow.activity_status(decisions, "PingWorker", None)
        self.assertTrue(return_value)
        return_value = self.workflow.activity_status(decisions, None, "PingWorker")
        self.assertTrue(return_value)
