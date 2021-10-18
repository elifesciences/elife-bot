import unittest
from collections import OrderedDict
from mock import patch
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.objects import Starter, default_workflow_params
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeLayer1
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

    @patch("boto.swf.layer1.Layer1")
    def test_connect_to_swf(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        self.starter.connect_to_swf()
        self.assertIsNotNone(self.starter.conn)

    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow_execution(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        workflow_params = {}
        self.starter.start_workflow_execution(workflow_params)
        self.assertEqual(self.logger.loginfo[-1], "got response: \nnull")

    @patch.object(FakeLayer1, "start_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_workflow_execution_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError(
            "message", None
        )
        workflow_params = {}
        self.starter.start_workflow_execution(workflow_params)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "SWFWorkflowExecutionAlreadyStartedError: "
                "There is already a running workflow with ID None"
            ),
        )

    @patch("boto.swf.layer1.Layer1")
    def test_start_swf_workflow_execution(self, fake_conn):
        fake_conn.return_value = FakeLayer1()
        workflow_params = {}
        self.starter.start_swf_workflow_execution(workflow_params)
        self.assertEqual(self.logger.loginfo[-1], "got response: \nnull")

    @patch.object(FakeLayer1, "start_workflow_execution")
    @patch("boto.swf.layer1.Layer1")
    def test_start_swf_workflow_execution_exception(self, fake_conn, fake_start):
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError(
            "message", None
        )
        workflow_params = {}
        with self.assertRaises(SWFWorkflowExecutionAlreadyStartedError):
            self.starter.start_swf_workflow_execution(workflow_params)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "SWFWorkflowExecutionAlreadyStartedError: "
                "There is already a running workflow with ID None"
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
