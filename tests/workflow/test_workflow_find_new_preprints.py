import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_FindNewPreprints import workflow_FindNewPreprints


class TestWorkflowFindNewPreprints(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_FindNewPreprints(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "FindNewPreprints")
