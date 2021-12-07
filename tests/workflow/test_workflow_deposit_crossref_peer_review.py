import unittest
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_DepositCrossrefPeerReview import (
    workflow_DepositCrossrefPeerReview,
)


class TestWorkflowDepositCrossrefPeerReview(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_DepositCrossrefPeerReview(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "DepositCrossrefPeerReview")
