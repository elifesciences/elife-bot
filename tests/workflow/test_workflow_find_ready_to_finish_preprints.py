import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_FindReadyToFinishPreprints import (
    workflow_FindReadyToFinishPreprints,
)


class TestWorkflowFindReadyToFinishPreprints(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_FindReadyToFinishPreprints(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "FindReadyToFinishPreprints")
