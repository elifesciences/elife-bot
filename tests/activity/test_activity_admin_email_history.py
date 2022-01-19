import unittest
from mock import patch
import provider.swfmeta as swfmetalib
import activity.activity_AdminEmailHistory as activity_module
from activity.activity_AdminEmailHistory import (
    activity_AdminEmailHistory as activity_object,
)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeSMTPServer, FakeSWFClient


class TestAdminEmailHistory(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch.object(swfmetalib.SWFMeta, "connect")
    @patch.object(swfmetalib.SWFMeta, "get_closed_workflow_execution_count")
    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_do_activity(
        self, fake_email_smtp_connect, fake_workflow_count, fake_swf_connect
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_swf_connect.return_value = FakeSWFClient()
        fake_workflow_count.return_value = 0
        success = self.activity.do_activity()
        self.assertEqual(success, True)


if __name__ == "__main__":
    unittest.main()
