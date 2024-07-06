import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_FindNewDocmaps import workflow_FindNewDocmaps


class TestWorkflowFindNewDocmaps(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_FindNewDocmaps(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "FindNewDocmaps")
