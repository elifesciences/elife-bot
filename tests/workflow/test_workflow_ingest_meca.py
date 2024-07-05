import unittest
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_IngestMeca import workflow_IngestMeca


class TestWorkflowIngestMeca(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_IngestMeca(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "IngestMeca")
