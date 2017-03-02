import unittest
from ssl import SSLError
from activity.activity_UpdateRepository import activity_UpdateRepository
import settings_mock
from mock import mock, patch, MagicMock
#from testfixtures import tempdir, compare
#import os
from activity.activity import activity
from classes_mock import FakeStorageContext
#from classes_mock import FakeSession
#import classes_mock
#import test_activity_data as testdata
#from ddt import ddt, data
#import helpers

class TestUpdateRepository(unittest.TestCase):

    @patch('activity.activity_UpdateRepository.lax_provider')
    @patch('activity.activity_UpdateRepository.StorageContext')
    @patch('dashboard_queue.send_message')
    def test_ssl_timeout_error_leads_to_a_retry(self, dashboard_queue, mock_storage_context, mock_lax_provider):
        a = activity_UpdateRepository(settings_mock, MagicMock())
        mock_storage_context.return_value = FakeStorageContext()
        mock_lax_provider.get_xml_file_name = MagicMock()
        a.update_github = MagicMock()
        a.update_github.side_effect = SSLError('The read operation timed out')
        result = a.do_activity({
            'article_id': '12345',
            'version': 1,
            'run': '123abc',
        })
        self.assertEqual(result, 'ActivityTemporaryFailure')

