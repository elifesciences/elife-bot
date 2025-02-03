import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_SilentIngestMeca import workflow_SilentIngestMeca


class TestWorkflowSilentIngestMeca(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_SilentIngestMeca(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "SilentIngestMeca")
