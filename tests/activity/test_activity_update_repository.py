import unittest
from ssl import SSLError
from activity.activity_UpdateRepository import activity_UpdateRepository
import settings_mock
from mock import patch, MagicMock
from activity.activity import activity
from classes_mock import FakeStorageContext, FakeLogger, FakeLaxProvider

@patch('activity.activity_UpdateRepository.provider')
@patch('activity.activity_UpdateRepository.storage_context')
@patch('dashboard_queue.send_message')
class TestUpdateRepository(unittest.TestCase):

    def test_ssl_timeout_error_leads_to_a_retry(self, dashboard_queue, mock_storage_context, provider):
        a = activity_UpdateRepository(settings_mock, FakeLogger())
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider()
        a.update_github = MagicMock()

        a.update_github.side_effect = SSLError('The read operation timed out')

        result = a.do_activity({
            'article_id': '12345',
            'version': 1,
            'run': '123abc',
        })
        self.assertEqual(result, 'ActivityTemporaryFailure')

