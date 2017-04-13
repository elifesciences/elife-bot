import unittest
import settings_mock
from activity.activity_VerifyImageServer import activity_VerifyImageServer
import test_activity_data as test_data
from mock import patch, MagicMock
from classes_mock import FakeSession
from ddt import ddt, data

class FakeStorageContext:
    def list_resources(self, resource):
        return ['elife-003530-fig1-v1-1022w.jpg',
                'elife-003530-fig1-v1-80w.jpg',
                'elife-003530-fig1-v1-1022w.gif',
                'elife-003530-fig1-v1.jpg',
                'elife-003530-fig1-v1.tif',
                'elife-003530-fig1-v1-download.jpg',
                'elife-003530-fig1-v1-download.xml']


class TestVerifyImageServer(unittest.TestCase):
    def setUp(self):
        self.verifyimageserver = activity_VerifyImageServer(settings_mock, None, None, None, None)

    @patch('activity.activity_VerifyImageServer.StorageContext')
    @patch('activity.activity_VerifyImageServer.Session')
    @patch.object(activity_VerifyImageServer,'retrieve_endpoints_check')
    def test_do_activity_success(self, fake_retrieve_endpoints_check, fake_session, fake_storage_context):
        # Given
        data = test_data.data_example_before_publish
        fake_retrieve_endpoints_check.return_value = [(True, "test.path")]
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        self.verifyimageserver.emit_monitor_event = MagicMock()
        self.verifyimageserver.logger = MagicMock()
        # When
        result = self.verifyimageserver.do_activity(data)
        # Then
        self.assertEqual(result, self.verifyimageserver.ACTIVITY_SUCCESS)

    @patch('activity.activity_VerifyImageServer.StorageContext')
    @patch('activity.activity_VerifyImageServer.Session')
    @patch.object(activity_VerifyImageServer,'retrieve_endpoints_check')
    def test_do_activity_failure(self, fake_retrieve_endpoints_check, fake_session, fake_storage_context):
        # Given
        data = test_data.data_example_before_publish
        fake_retrieve_endpoints_check.return_value = [(False, "test.path")]
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        self.verifyimageserver.emit_monitor_event = MagicMock()
        self.verifyimageserver.logger = MagicMock()
        # When
        result = self.verifyimageserver.do_activity(data)
        # Then
        self.assertEqual(result, self.verifyimageserver.ACTIVITY_PERMANENT_FAILURE)

    @patch('activity.activity_VerifyImageServer.StorageContext')
    @patch('activity.activity_VerifyImageServer.Session')
    @patch.object(activity_VerifyImageServer,'retrieve_endpoints_check')
    def test_do_activity_error(self, fake_retrieve_endpoints_check, fake_session, fake_storage_context):
        # Given
        data = test_data.data_example_before_publish
        fake_retrieve_endpoints_check.side_effect = Exception("Error!")
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        self.verifyimageserver.emit_monitor_event = MagicMock()
        self.verifyimageserver.logger = MagicMock()
        # When
        result = self.verifyimageserver.do_activity(data)
        # Then
        self.assertEqual(result, self.verifyimageserver.ACTIVITY_PERMANENT_FAILURE)

