import unittest
from mock import patch
import activity.activity_VersionReasonDecider as activity_module
from activity.activity_VersionReasonDecider import activity_VersionReasonDecider as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSQSQueue, FakeSession, FakeSQSMessage
from testfixtures import TempDirectory


TEST_DATA = {
    'run': '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
    'version_reason': 'version reason text',
    'scheduled_publication_date': '1518688960'
}

SESSION_EXAMPLE = {
    'expanded_folder': '7777777701234.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
    'article_id': '7777777701234',
    'version': '1',
    'update_date': '2012-12-13T00:00:00Z',
    'status': 'vor'
    }


class TestVersionReasonDecider(unittest.TestCase):

    def setUp(self):
        patcher = patch('boto.sqs.connect_to_region', spec=True)
        patcher.start()
        self.activity = activity_object(settings_mock, FakeLogger(), None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, 'Message')
    @patch('boto.sqs.connection.SQSConnection.get_queue')
    @patch.object(activity_object, 'emit_monitor_event')
    @patch.object(activity_module, 'get_session')
    def test_do_activity_success(self, fake_session, fake_emit_monitor,
                                 fake_sqs_queue, fake_sqs_message):
        fake_session.return_value = FakeSession(SESSION_EXAMPLE)
        fake_sqs_queue.return_value = FakeSQSQueue(TempDirectory())
        fake_sqs_message.return_value = FakeSQSMessage(TempDirectory())
        result = self.activity.do_activity(TEST_DATA)
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)


if __name__ == '__main__':
    unittest.main()
