import unittest
from activity.activity_RewriteEIF import activity_RewriteEIF
import settings_mock
import test_activity_data as data
from mock import mock, patch
from classes_mock import FakeKey
from classes_mock import FakeS3Connection
from classes_mock import FakeSession
import classes_mock
from testfixtures import TempDirectory
import json



class tests_RewriteEIF(unittest.TestCase):
    def setUp(self):
        self.activity_PreparePostEIF = activity_RewriteEIF(
            settings_mock, None, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('activity.activity_RewriteEIF.eif_provider.Key')
    @patch('activity.activity_RewriteEIF.get_session')
    @patch('activity.activity_RewriteEIF.S3Connection')
    @patch.object(activity_RewriteEIF, 'emit_monitor_event')
    @patch.object(activity_RewriteEIF, 'set_monitor_property')
    def test_activity(self, mock_set_monitor_property, mock_emit_monitor_event, fake_s3_mock, fake_session, fake_key_mock):
        directory = TempDirectory()

        fake_session.return_value = FakeSession(data.session_example)
        fake_key_mock.return_value = FakeKey(directory, data.bucket_dest_file_name,
                                             data.RewriteEIF_json_input_string)
        fake_s3_mock.return_value = FakeS3Connection()

        success = self.activity_PreparePostEIF.do_activity(data.RewriteEIF_data)
        self.assertEqual(True, success)

        output_json = json.loads(directory.read(data.bucket_dest_file_name))
        expected = data.RewriteEIF_json_output
        self.assertDictEqual(output_json, expected)

if __name__ == '__main__':
    unittest.main()
