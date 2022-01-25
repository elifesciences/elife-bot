import unittest
from mock import patch
from tests import read_fixture, settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger
from workflow.objects import Workflow, WorkflowLayer1Decisions
from workflow.helper import define_workflow_step


def decisions_data():
    return read_fixture("decision_events.py")


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


class TestWorkflowLayer1Decisions(unittest.TestCase):
    def setUp(self):
        self.decisions = WorkflowLayer1Decisions()

    def test_fail_workflow_execution(self):
        self.decisions.fail_workflow_execution("reason")
        expected = [
            {
                "decisionType": "FailWorkflowExecution",
                "failWorkflowExecutionDecisionAttributes": {},
            },
            {
                "decisionType": "FailWorkflowExecution",
                "failWorkflowExecutionDecisionAttributes": {"reason": "reason"},
            },
        ]
        self.assertEqual(self.decisions.data, expected)

    def test_fail_workflow_execution_no_reason(self):
        self.decisions.fail_workflow_execution()
        expected = [
            {
                "decisionType": "FailWorkflowExecution",
                "failWorkflowExecutionDecisionAttributes": {},
            },
        ]
        self.assertEqual(self.decisions.data, expected)


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        logger = FakeLogger()
        swf_client = FakeSWFClient()
        self.workflow = Workflow(settings_mock, logger, swf_client, None, None, None)

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

    def test_is_workflow_complete_false(self):
        "test is not complete"
        self.workflow.definition = {"steps": [define_workflow_step("Ping", None)]}
        self.workflow.decision = {"events": []}
        self.assertFalse(self.workflow.is_workflow_complete())

    def test_is_workflow_complete_true(self):
        "test is complete"
        self.workflow.definition = {"steps": [define_workflow_step("Ping", None)]}
        self.workflow.decision = {
            "events": [
                {
                    "eventType": "ActivityTaskScheduled",
                    "activityTaskScheduledEventAttributes": {
                        "activityType": {"version": "1", "name": "Ping"},
                        "activityId": "Ping",
                    },
                    "eventId": 15,
                },
                {
                    "eventType": "ActivityTaskCompleted",
                    "activityTaskCompletedEventAttributes": {
                        "scheduledEventId": 15,
                    },
                    "eventId": 18,
                },
            ]
        }
        self.assertTrue(self.workflow.is_workflow_complete())

    def test_is_workflow_complete_parallel_false(self):
        "test parallel steps is not complete"
        self.workflow.definition = {
            "steps": [
                [
                    define_workflow_step("Ping", None, activity_id="Ping1"),
                    define_workflow_step("Ping", None, activity_id="Ping2"),
                ]
            ]
        }
        self.workflow.decision = {"events": []}
        self.assertFalse(self.workflow.is_workflow_complete())

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
        first_decision_type = decisions.data[0].get("decisionType")
        first_decision_attrs = decisions.data[0].get(
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

    def test_last_activity_status_completed(self):
        decision_events = {"events": [{"eventType": "ActivityTaskCompleted"}]}
        self.assertEqual(
            self.workflow.last_activity_status(decision_events), "ActivityTaskCompleted"
        )

    def test_last_activity_status_failed(self):
        decision_events = {"events": [{"eventType": "ActivityTaskFailed"}]}
        self.assertEqual(
            self.workflow.last_activity_status(decision_events), "ActivityTaskFailed"
        )

    @patch("boto3.client")
    def test_handle_next_page_token(self, fake_client):
        fake_client.return_value = FakeSWFClient
        self.workflow.decision = {
            "events": [{"eventType": "ActivityTaskFailed"}],
            "nextPageToken": "foo",
        }
        self.assertFalse(self.workflow.handle_nextPageToken())

    def test_handle_next_page_token_key_error(self):
        self.workflow.decision = {}
        self.assertIsNone(self.workflow.handle_nextPageToken())

    def test_get_input(self):
        self.workflow.decision = {
            "events": [
                {
                    "workflowExecutionStartedEventAttributes": {
                        "input": '{"data": [1,3,7,11]}',
                    },
                }
            ]
        }
        expected = {"data": [1, 3, 7, 11]}
        self.assertEqual(self.workflow.get_input(), expected)

    def test_get_input_key_error(self):
        self.workflow.decision = {"events": [{}]}
        self.assertIsNone(self.workflow.get_input())

    def test_get_input_no_decision_events(self):
        self.assertIsNone(self.workflow.get_input())

    @patch.object(Workflow, "complete_decision")
    def test_check_for_failed_workflow_request(self, fake_complete):
        fake_complete.return_value = True
        decision_events = {
            "events": [{"eventType": "WorkflowExecutionCancelRequested"}]
        }
        self.assertIsNone(
            self.workflow.check_for_failed_workflow_request(decision_events)
        )

    def test_check_for_failed_workflow_request_type_error(self):
        decision_events = None
        self.assertIsNone(
            self.workflow.check_for_failed_workflow_request(decision_events)
        )

    @patch("time.sleep")
    def test_rate_limit_failed_activity(self, fake_sleep):
        fake_sleep.return_value = True
        decision_events = {"events": [{"eventType": "ActivityTaskFailed"}]}
        self.assertIsNone(self.workflow.rate_limit_failed_activity(decision_events))

    def test_rate_limit_failed_activity_type_error(self):
        decision_events = None
        self.assertIsNone(self.workflow.rate_limit_failed_activity(decision_events))
