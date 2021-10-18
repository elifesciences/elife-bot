import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_PubRouterDeposit import starter_PubRouterDeposit
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeLayer1
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


class TestStarterPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_PubRouterDeposit(settings_mock, self.logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "PubRouterDeposit_HEFCE"),
                ("workflow_name", "PubRouterDeposit"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                ("input", '{"data": {"workflow": "HEFCE"}}'),
            ]
        )
        params = self.starter.get_workflow_params(workflow="HEFCE")
        self.assertEqual(params, expected)

    def test_get_workflow_params_no_workflow(self):
        with self.assertRaises(NullRequiredDataException) as test_exception:
            self.starter.get_workflow_params()
        self.assertEqual(
            str(test_exception.exception), "Did not get a workflow argument. Required."
        )

    @patch("boto.swf.layer1.Layer1")
    def test_start(self, fake_conn):
        workflow = "HEFCE"
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, workflow))
