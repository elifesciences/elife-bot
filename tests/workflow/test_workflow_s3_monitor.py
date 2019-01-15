import unittest
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from workflow.workflow_S3Monitor import workflow_S3Monitor


class TestWorkflowS3Monitor(unittest.TestCase):
    def setUp(self):
        self.workflow = workflow_S3Monitor(
            settings_mock, FakeLogger(), None, None, None, None)

    def test_init(self):
        self.assertEqual(self.workflow.name, 'S3Monitor')
