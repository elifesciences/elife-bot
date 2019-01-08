import unittest
import json
from tests import settings_mock
import decider


class TestDecider(unittest.TestCase):

    def setUp(self):
        self.decision_json = None
        with open('tests/test_data/decision.json', 'rb') as open_file:
            self.decision_json = json.loads(open_file.read())

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


if __name__ == '__main__':
    unittest.main()
