import unittest
from provider.simpleDB import SimpleDB
from boto.swf.exceptions import SWFWorkflowExecutionAlreadyStartedError
from starter.starter_PackagePOA import starter_PackagePOA
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
from mock import patch


class TestStarterPackagePOA(unittest.TestCase):
    def setUp(self):
        self.starter = starter_PackagePOA()

    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_conn):
        document = 'document'
        last_updated_since = None
        fake_conn.return_value = FakeLayer1()
        self.assertIsNone(self.starter.start(settings_mock, document, last_updated_since))

    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    def test_start_exception(self, fake_conn, fake_start):
        document = 'document'
        last_updated_since = None
        fake_conn.return_value = FakeLayer1()
        fake_start.side_effect = SWFWorkflowExecutionAlreadyStartedError("message", None)
        self.assertIsNone(self.starter.start(settings_mock, document, last_updated_since))

    @patch.object(SimpleDB, 'elife_get_POA_delivery_S3_file_items')
    def test_get_docs_from_simple_db(self, fake_file_items):
        fake_file_items.return_value = [
            {
                'name': 'document'
            }
        ]
        last_updated_since = 'a date'
        docs = self.starter.get_docs_from_SimpleDB(settings_mock, FakeLogger(), last_updated_since)
        self.assertEqual(len(docs), 1)


if __name__ == '__main__':
    unittest.main()
