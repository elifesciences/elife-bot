import unittest
import json
from mock import patch
from tests import read_fixture, settings_mock
from tests.classes_mock import FakeFlag, FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import decider
from workflow.workflow_Ping import workflow_Ping as workflow_object


class TestDecider(unittest.TestCase):
    def setUp(self):
        self.decision_events = read_fixture("decision_events.py")

    def test_get_task_token(self):
        expected = (
            "AAAAKgAAAAEAAAAAAAAAAjaHv5Lk1csWNpSpgCC0bOKbWQv8HfmDMCyp6HvCbcrjeH2ao+M+Jz76e+wNuk"
            + "EX6cyLCf+LEBQmUy83b6Abd1HhduEQ/imaw2YftjNt20QtS75QXgPzOIFQ6rh43MKDwBCcnUpttjUzqiev"
            + "a2Y1eEisq4Ax7pZ+ydKmYBFodCvt48BPFD48L7qtmh14rpF2ic8AuNakilIhG3IL5s/UX1gMLre39Rd03U"
            + "gK+0KuozCIfXwSU+wILRuSOaNB7cHDhiBFg12FSrUFXRHZVZr/qFhGXCEmLNjf/rOpNC1UoZwV"
        )
        task_token = decider.get_task_token(self.decision_events)
        self.assertEqual(task_token, expected)

    def test_get_task_token_failure(self):
        task_token = decider.get_task_token({})
        self.assertIsNone(task_token)

    def test_get_workflow_type(self):
        expected = "Sum"
        workflow_type = decider.get_workflow_type(self.decision_events)
        self.assertEqual(workflow_type, expected)

    def test_get_workflow_type_failure(self):
        workflow_type = decider.get_workflow_type({})
        self.assertIsNone(workflow_type)

    @patch.object(FakeSWFClient, "poll_for_decision_task")
    def test_get_all_paged_events(self, fake_poll):
        decision_events = read_fixture("decision_next_page_token.py")
        polled_decision_json = {"events": ["something"]}
        fake_client = FakeSWFClient()
        fake_poll.return_value = polled_decision_json
        decision = decider.get_all_paged_events(
            decision_events, fake_client, None, None, None, None
        )
        self.assertEqual(decision.get("events"), polled_decision_json.get("events"))

    def test_get_input(self):
        expected = {"data": [1, 3, 7, 11]}
        decider_input = decider.get_input(self.decision_events)
        self.assertEqual(decider_input, expected)

    def test_get_input_failure(self):
        decider_input = decider.get_input({})
        self.assertIsNone(decider_input)

    def test_get_workflow_name(self):
        workflow_type = "Ping"
        expected = "workflow_Ping"
        workflow_name = decider.get_workflow_name(workflow_type)
        self.assertEqual(workflow_name, expected)

    def test_import_workflow_class(self):
        workflow_name = "workflow_Ping"
        result = decider.import_workflow_class(workflow_name)
        self.assertTrue(result)

    def test_import_workflow_class_failure(self):
        workflow_name = "this_workflow_does_not_exist"
        result = decider.import_workflow_class(workflow_name)
        self.assertFalse(result)

    def test_get_workflow_object(self):
        workflow_name = "workflow_Ping"
        decider.import_workflow_class(workflow_name)
        workflow_object = decider.get_workflow_object(
            workflow_name, settings_mock, None, None, None, None, None
        )
        self.assertEqual(workflow_object.__class__.__name__, workflow_name)


class TestDeciderDecide(unittest.TestCase):
    def setUp(self):
        self.flag = FakeFlag(0.25)
        self.logger = FakeLogger()

    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_decision_task")
    @patch("boto3.client")
    def test_decide(self, fake_client, fake_poll, fake_get_logger):
        "test will not be able to find workflow_Sum, which no longer exists"
        decision_events = read_fixture("decision_events.py")
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        fake_poll.return_value = decision_events
        # invoke decide
        decider.decide(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "error: could not load object workflow_Sum" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_decision_task")
    @patch("boto3.client")
    def test_decide_started_event_id(self, fake_client, fake_poll, fake_get_logger):
        "test for coverage of when startedEventId is 0"
        decision_json = {"startedEventId": 0}
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        fake_poll.return_value = decision_json
        # invoke decide
        decider.decide(settings_mock, self.flag)
        # make some assertions on debug log
        self.assertTrue("got decision:" in self.logger.logdebug)

    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_decision_task")
    @patch("boto3.client")
    def test_decide_ping(self, fake_client, fake_poll, fake_get_logger):
        "test based on cron_FiveMinute workflow with just a Ping activity"
        decision_events = read_fixture("decision_ping.py")
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        fake_poll.return_value = decision_events
        # invoke decide
        decider.decide(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue("scheduling task: PingWorker" in self.logger.loginfo)
        self.assertTrue("workflow_Ping success True" in self.logger.loginfo)

    @patch.object(workflow_object, "do_workflow")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_decision_task")
    @patch("boto3.client")
    def test_decide_ping_workflow_exception(
        self, fake_client, fake_poll, fake_get_logger, fake_do_workflow
    ):
        "test cron_FiveMinute workflow raising an exception"
        decision_events = read_fixture("decision_ping.py")
        fake_do_workflow.side_effect = Exception("An exception")
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        fake_poll.return_value = decision_events
        # invoke decide
        decider.decide(settings_mock, self.flag)
        # make assertions on error log
        self.assertTrue("error processing workflow" in self.logger.logerror)


class TestTrimmedDecision(unittest.TestCase):
    def setUp(self):
        self.decision_events = read_fixture("decision_events.py")

    def test_trimmed_decision(self):
        decision_trimmed = decider.trimmed_decision(self.decision_events)
        self.assertEqual(decision_trimmed.get("events"), [])
        # original is unchanged
        self.assertEqual(len(self.decision_events.get("events")), 22)

    def test_trimmed_decision_debug(self):
        decision_trimmed = decider.trimmed_decision(self.decision_events, True)
        self.assertEqual(len(decision_trimmed.get("events")), 22)
        # original is unchanged
        self.assertEqual(len(self.decision_events.get("events")), 22)


if __name__ == "__main__":
    unittest.main()
