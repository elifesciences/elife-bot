import unittest
from mock import patch
from provider.simpleDB import SimpleDB
import provider.swfmeta as swfmetalib
from activity.activity_AdminEmailHistory import activity_AdminEmailHistory as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


class TestAdminEmailHistory(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch.object(swfmetalib.SWFMeta, 'get_closed_workflow_execution_count')
    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    def test_do_activity(self, fake_email, fake_workflow_count):
        fake_workflow_count.return_value = 0
        success = self.activity.do_activity()
        self.assertEqual(success, True)


if __name__ == '__main__':
    unittest.main()
