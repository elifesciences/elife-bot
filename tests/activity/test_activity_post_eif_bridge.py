import unittest
from activity.activity_PostEIFBridge import activity_PostEIFBridge
import settings_mock
import test_activity_data as test_data
from mock import mock, patch, call
from ddt import ddt, data
from classes_mock import FakeSQSConn
from classes_mock import FakeSQSMessage
from classes_mock import FakeSQSQueue
from classes_mock import FakeLogger
from classes_mock import FakeSession
from testfixtures import TempDirectory
import json
import base64

test_publication_data = {
            'workflow_name': 'PostPerfectPublication',
            'workflow_data':
                {'status': u'vor',
                 'update_date': u'2012-12-13T00:00:00Z',
                 'run': u'cf9c7e86-7355-4bb4-b48e-0bc284221251',
                 'expanded_folder': u'00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251',
                 'version': u'1',
                 'eif_location': '00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251/elife-00353-v1.json',
                 'article_id': u'00353'}
            }

@ddt
class tests_PostEIFBridge(unittest.TestCase):
    def setUp(self):
        self.activity_PostEIFBridge = activity_PostEIFBridge(settings_mock, None, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('activity.activity_PostEIFBridge.get_session')
    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    @patch.object(activity_PostEIFBridge, 'set_monitor_property')
    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PostEIFBridge.Message')
    def test_activity_published_article(self, mock_sqs_message, mock_sqs_connect,
                                        mock_set_monitor_property, mock_emit_monitor_event,
                                        fake_get_session):

        directory = TempDirectory()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)

        fake_session = FakeSession({'published': True})
        fake_get_session.return_value = fake_session
        # prime the session with data that would be set by an earlier activity
        fake_session.store_value('article_path', 'content/1/e00353v1')

        data = test_data.PostEIFBridge_data(True, u'2012-12-13T00:00:00Z')

        #When
        success = self.activity_PostEIFBridge.do_activity(data)

        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(test_data.PostEIFBridge_test_dir)

        #Then
        self.assertEqual(True, success)

        self.assertEqual(json.dumps(test_data.PostEIFBridge_message), data_written_in_test_queue)

        mock_set_monitor_property.assert_has_calls(
            [call(settings_mock, data["article_id"], "path", data['article_path'], "text", version="1")
            ,call(settings_mock, data["article_id"], "publication-status", "published", "text", version="1")])

        mock_emit_monitor_event.assert_called_with(settings_mock, data["article_id"], data["version"], data["run"],
                                                   "Post EIF Bridge", "end",
                                                   "Finished Post EIF Bridge " + data["article_id"])

    @data(test_publication_data)
    @patch('activity.activity_PostEIFBridge.get_session')
    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    @patch.object(activity_PostEIFBridge, 'set_monitor_property')
    def test_activity_unpublished_article(self, expected_publication_data, mock_set_monitor_property,
                                          mock_emit_monitor_event, fake_get_session):

        fake_session = FakeSession({'published': False})
        fake_get_session.return_value = fake_session

        #Given
        data = test_data.PostEIFBridge_data(False, u'2012-12-13T00:00:00Z')

        #When
        success = self.activity_PostEIFBridge.do_activity(data)

        #Then
        self.assertEqual(True, success)

        mock_set_monitor_property.assert_has_calls(
            [call(settings_mock, data["article_id"], "_publication-data",
                  base64.encodestring(json.dumps(expected_publication_data)), "text", version=data["version"])
            ,call(settings_mock, data["article_id"], "publication-status",
                  "ready to publish", "text", version=data["version"])]
        )

        mock_emit_monitor_event.assert_called_with(settings_mock, data["article_id"], data["version"], data["run"],
                                                   "Post EIF Bridge", "end",
                                                   "Finished Post EIF Bridge " + data["article_id"])

    @patch('activity.activity_PostEIFBridge.get_session')
    @patch('boto.sqs.connect_to_region')
    @patch('activity.activity_PostEIFBridge.Message')
    def test_activity_published_article_no_update_date(self, mock_sqs_message, mock_sqs_connect,
                                                       fake_get_session):
        directory = TempDirectory()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_sqs_message.return_value = FakeSQSMessage(directory)
        fake_session = FakeSession({'published': True})
        fake_get_session.return_value = fake_session
        self.activity_PostEIFBridge.set_monitor_property = mock.MagicMock()
        self.activity_PostEIFBridge.emit_monitor_event = mock.MagicMock()
        success = self.activity_PostEIFBridge.do_activity(test_data.PostEIFBridge_data(True, None))
        fake_sqs_queue = FakeSQSQueue(directory)
        data_written_in_test_queue = fake_sqs_queue.read(test_data.PostEIFBridge_test_dir)
        self.assertEqual(True, success)
        self.assertEqual(json.dumps(test_data.PostEIFBridge_message_no_update_date), data_written_in_test_queue)

    @patch('activity.activity_PostEIFBridge.get_session')
    @patch.object(activity_PostEIFBridge, 'emit_monitor_event')
    def test_activity_exception(self, mock_emit_monitor_event, fake_get_session):

        fake_logger = FakeLogger()
        fake_session = FakeSession({'published': False})
        fake_get_session.return_value = fake_session
        self.activity_PostEIFBridge_with_log = activity_PostEIFBridge(settings_mock, fake_logger, None, None, None)

        data = test_data.PostEIFBridge_data(False, u'2012-12-13T00:00:00Z')

        #When
        success = self.activity_PostEIFBridge_with_log.do_activity(data)

        #Then
        self.assertRaises(Exception)
        self.assertEqual("Exception after submitting article EIF", fake_logger.logexception)

        mock_emit_monitor_event.assert_called_with(settings_mock, data["article_id"], data["version"], data["run"],
                                                   "Post EIF Bridge", "error",
                                                   "Error carrying over information after EIF For "
                                                   "article 00353 message:'NoneType' object has no "
                                                   "attribute 'publish'")

        self.assertEqual(False, success)

if __name__ == '__main__':
    unittest.main()
