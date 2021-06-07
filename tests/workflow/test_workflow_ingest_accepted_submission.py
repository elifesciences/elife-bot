import unittest
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_IngestAcceptedSubmission import workflow_IngestAcceptedSubmission


class TestWorkflowIngestAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_IngestAcceptedSubmission(
            settings_mock, FakeLogger(), None, None, None, None
        )

    def test_init(self):
        self.assertEqual(self.workflow.name, "IngestAcceptedSubmission")
