import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_FindFuturePreprints import workflow_FindFuturePreprints


class TestWorkflowFindFuturePreprints(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_FindFuturePreprints(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "FindFuturePreprints")
