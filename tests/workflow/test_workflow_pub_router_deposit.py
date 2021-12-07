import unittest
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_PubRouterDeposit import workflow_PubRouterDeposit


class TestWorkflowPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "PubRouterDeposit")
