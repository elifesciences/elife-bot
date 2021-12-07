import unittest
from workflow.helper import define_workflow_step


class TestDefineWorkflowStep(unittest.TestCase):
    def test_define_workflow_step(self):
        """test defaults for define_workflow_step"""
        activity_type = "Name"
        activity_input = None
        step_definition = define_workflow_step(activity_type, activity_input)
        self.assertEqual(step_definition.get("activity_type"), activity_type)
        self.assertEqual(step_definition.get("input"), activity_input)
        self.assertEqual(step_definition.get("activity_id"), activity_type)
        self.assertEqual(step_definition.get("version"), "1")
        self.assertIsNone(step_definition.get("control"))
        self.assertEqual(step_definition.get("heartbeat_timeout"), 60 * 5)
        self.assertEqual(step_definition.get("schedule_to_close_timeout"), 60 * 5)
        self.assertEqual(step_definition.get("schedule_to_start_timeout"), 60 * 5)
        self.assertEqual(step_definition.get("start_to_close_timeout"), 60 * 5)

    def test_define_workflow_step_override(self):
        """test overriding values for define_workflow_step"""
        activity_type = "Name"
        activity_input = {"data": "foo"}
        activity_id = "Name_01"
        version = "2"
        control = "control data"
        heartbeat_timeout = 60 * 10
        schedule_to_close_timeout = 60 * 10
        schedule_to_start_timeout = 60 * 10
        start_to_close_timeout = 60 * 10
        step_definition = define_workflow_step(
            activity_type,
            activity_input,
            activity_id,
            version,
            control,
            heartbeat_timeout,
            schedule_to_close_timeout,
            schedule_to_start_timeout,
            start_to_close_timeout,
        )
        self.assertEqual(step_definition.get("activity_type"), activity_type)
        self.assertEqual(step_definition.get("input"), activity_input)
        self.assertEqual(step_definition.get("activity_id"), activity_id)
        self.assertEqual(step_definition.get("version"), version)
        self.assertEqual(step_definition.get("control"), control)
        self.assertEqual(
            step_definition.get("heartbeat_timeout"), schedule_to_close_timeout
        )
        self.assertEqual(
            step_definition.get("schedule_to_close_timeout"), schedule_to_start_timeout
        )
        self.assertEqual(
            step_definition.get("schedule_to_start_timeout"), start_to_close_timeout
        )
        self.assertEqual(
            step_definition.get("start_to_close_timeout"), start_to_close_timeout
        )
