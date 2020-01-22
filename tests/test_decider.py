import unittest
import json
from mock import patch
from tests import settings_mock
from tests.classes_mock import FakeFlag, FakeLayer1
from tests.activity.classes_mock import FakeLogger
import decider


class TestDecider(unittest.TestCase):

    def setUp(self):
        self.decision_json = None
        with open('tests/test_data/decision.json', 'r') as open_file:
            self.decision_json = json.loads(open_file.read())

    @patch('logging.getLogger')
    @patch.object(FakeLayer1, 'poll_for_decision_task')
    @patch('boto.swf.layer1.Layer1')
    def test_decide(self, fake_conn, fake_poll, fake_get_logger):
        """test will not be able to find workflow_Sum, which no longer exists"""
        flag = FakeFlag()
        fake_logger = FakeLogger()
        fake_get_logger.return_value = fake_logger
        fake_conn.return_value = FakeLayer1()
        fake_poll.return_value = self.decision_json
        decider.decide(settings_mock, flag)
        # make some assertions on log values
        self.assertTrue('error: could not load object workflow_Sum' in fake_logger.loginfo)
        self.assertTrue(fake_logger.loginfo.endswith('graceful shutdown'))

    @patch('logging.getLogger')
    @patch.object(FakeLayer1, 'poll_for_decision_task')
    @patch('boto.swf.layer1.Layer1')
    def test_decide_started_event_id(self, fake_conn, fake_poll, fake_get_logger):
        """test for coverage of when startedEventId is 0"""
        decision_json = {'startedEventId': 0}
        flag = FakeFlag()
        fake_logger = FakeLogger()
        fake_get_logger.return_value = fake_logger
        fake_conn.return_value = FakeLayer1()
        fake_poll.return_value = decision_json
        decider.decide(settings_mock, flag)
        # make some assertions on log values
        self.assertTrue('got decision:' in fake_logger.logdebug)

    def test_get_task_token(self):
        expected = (
            'AAAAKgAAAAEAAAAAAAAAAjaHv5Lk1csWNpSpgCC0bOKbWQv8HfmDMCyp6HvCbcrjeH2ao+M+Jz76e+wNuk' +
            'EX6cyLCf+LEBQmUy83b6Abd1HhduEQ/imaw2YftjNt20QtS75QXgPzOIFQ6rh43MKDwBCcnUpttjUzqiev' +
            'a2Y1eEisq4Ax7pZ+ydKmYBFodCvt48BPFD48L7qtmh14rpF2ic8AuNakilIhG3IL5s/UX1gMLre39Rd03U' +
            'gK+0KuozCIfXwSU+wILRuSOaNB7cHDhiBFg12FSrUFXRHZVZr/qFhGXCEmLNjf/rOpNC1UoZwV')
        task_token = decider.get_taskToken(self.decision_json)
        self.assertEqual(task_token, expected)

    def test_get_task_token_failure(self):
        task_token = decider.get_taskToken({})
        self.assertIsNone(task_token)

    def test_get_workflow_type(self):
        expected = 'Sum'
        workflow_type = decider.get_workflowType(self.decision_json)
        self.assertEqual(workflow_type, expected)

    def test_get_workflow_type_failure(self):
        workflow_type = decider.get_workflowType({})
        self.assertIsNone(workflow_type)

    @patch.object(FakeLayer1, 'poll_for_decision_task')
    def test_get_all_paged_events(self, fake_poll):
        with open('tests/test_data/decision_nextPageToken.json', 'r') as open_file:
            decision_json = json.loads(open_file.read())
        polled_decision_json = {'events': ['something']}
        fake_conn = FakeLayer1()
        fake_poll.return_value = polled_decision_json
        decision = decider.get_all_paged_events(
            decision_json, fake_conn, None, None, None, None)
        self.assertEqual(decision.get('events'), polled_decision_json.get('events'))

    def test_get_input(self):
        expected = {'data': [1, 3, 7, 11]}
        decider_input = decider.get_input(self.decision_json)
        self.assertEqual(decider_input, expected)

    def test_get_input_failure(self):
        decider_input = decider.get_input({})
        self.assertIsNone(decider_input)

    def test_get_workflow_name(self):
        workflow_type = 'Ping'
        expected = 'workflow_Ping'
        workflow_name = decider.get_workflow_name(workflow_type)
        self.assertEqual(workflow_name, expected)

    def test_import_workflow_class(self):
        workflow_name = 'workflow_Ping'
        result = decider.import_workflow_class(workflow_name)
        self.assertTrue(result)

    def test_import_workflow_class_failure(self):
        workflow_name = 'this_workflow_does_not_exist'
        result = decider.import_workflow_class(workflow_name)
        self.assertFalse(result)

    def test_get_workflow_object(self):
        workflow_name = 'workflow_Ping'
        decider.import_workflow_class(workflow_name)
        workflow_object = decider.get_workflow_object(
            workflow_name, settings_mock, None, None, None, None, None)
        self.assertEqual(workflow_object.__class__.__name__, workflow_name)


class TestTrimmedDecision(unittest.TestCase):

    def setUp(self):
        self.decision_json = None
        with open('tests/test_data/decision.json', 'r') as open_file:
            self.decision_json = json.loads(open_file.read())

    def test_trimmed_decision(self):
        decision_trimmed = decider.trimmed_decision(self.decision_json)
        self.assertEqual(decision_trimmed.get('events'), [])
        # original is unchanged
        self.assertEqual(len(self.decision_json.get('events')), 22)

    def test_trimmed_decision_debug(self):
        decision_trimmed = decider.trimmed_decision(self.decision_json, True)
        self.assertEqual(len(decision_trimmed.get('events')), 22)
        # original is unchanged
        self.assertEqual(len(self.decision_json.get('events')), 22)


if __name__ == '__main__':
    unittest.main()
