import unittest
from mock import mock, patch
import activity.activity_ScheduleDownstream as activity_module
from activity.activity_ScheduleDownstream import activity_ScheduleDownstream as activity_object
from provider import article
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


class TestScheduleDownstream(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch('provider.lax_provider.article_first_by_status')
    @patch.object(article, 'storage_context')
    @patch.object(activity_module, 'storage_context')
    def test_do_activity(self, fake_activity_storage_context, fake_storage_context, fake_first):
        expected_result = True
        fake_storage_context.return_value = FakeStorageContext()
        fake_activity_storage_context.return_value = FakeStorageContext()
        fake_first.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        # check assertions
        self.assertEqual(result, expected_result)

    def test_choose_outboxes_poa_first(self):
        """first poa version"""
        outbox_list = activity_module.choose_outboxes("poa", activity_module.outbox_map(), True)
        self.assertTrue("pubmed/outbox/" in outbox_list)
        self.assertTrue("publication_email/outbox/" in outbox_list)
        self.assertFalse("pmc/outbox/" in outbox_list)

    def test_choose_outboxes_poa_not_first(self):
        """poa but not the first poa"""
        outbox_list = activity_module.choose_outboxes("poa", activity_module.outbox_map(), False)
        self.assertTrue("pubmed/outbox/" in outbox_list)
        # do not send to pmc
        self.assertFalse("pmc/outbox/" in outbox_list)
        # do not send publication_email
        self.assertFalse("publication_email/outbox/" in outbox_list)

    def test_choose_outboxes_vor_first(self):
        """first vor version"""
        outbox_list = activity_module.choose_outboxes("vor", activity_module.outbox_map(), True)
        self.assertTrue("pmc/outbox/" in outbox_list)
        self.assertTrue("publication_email/outbox/" in outbox_list)
        self.assertTrue("pub_router/outbox/" in outbox_list)

    def test_choose_outboxes_vor_not_first(self):
        """vor but not the first vor"""
        outbox_list = activity_module.choose_outboxes("vor", activity_module.outbox_map(), False)
        self.assertTrue("pmc/outbox/" in outbox_list)
        self.assertTrue("pub_router/outbox/" in outbox_list)
        # do not send publication_email
        self.assertFalse("publication_email/outbox/" in outbox_list)

    def test_choose_outboxes_vor_silent_first(self):
        outbox_list = activity_module.choose_outboxes(
            "vor", activity_module.outbox_map(), True, "silent-correction")
        self.assertTrue("pmc/outbox/" in outbox_list)
        # do not send publication_email
        self.assertFalse("publication_email/outbox/" in outbox_list)


if __name__ == '__main__':
    unittest.main()
