import unittest
from activity.activity_ConvertJATS import activity_ConvertJATS
import test_activity_data as data
import json
from testfixtures import tempdir, compare
from testfixtures import TempDirectory
from mock import mock, patch
from classes_mock import FakeSession
from classes_mock import FakeKey
from classes_mock import FakeS3Connection
import settings_mock
import test_activity_data as testdata


class TestConvertJATS(unittest.TestCase):
    def setUp(self):
        self.jats = activity_ConvertJATS(settings_mock, None, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_update_to_json(self):
        json_output_result = self.jats.add_update_date_to_json(data.json_output_parameter_example_string,'2012-12-13T00:00:00Z', None)
        self.assertDictEqual(json.loads(json_output_result), data.json_output_return_example)

    @tempdir()
    @patch.object(activity_ConvertJATS, 'add_update_date_to_json')
    @patch.object(activity_ConvertJATS, 'get_article_xml_key')
    @patch('activity.activity_ConvertJATS.Key')
    @patch('activity.activity_ConvertJATS.S3Connection')
    @patch('activity.activity_ConvertJATS.Session')
    def test_do_activity(self, fake_session_mock, fake_s3_mock, fake_key_mock, fake_get_article_xml_key, fake_add_update_date_to_json):
        directory = TempDirectory()

        #preparing Mocks
        fake_session_mock.return_value = FakeSession(data.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        fake_key_mock.return_value = FakeKey(directory, data.bucket_dest_file_name)
        fake_get_article_xml_key.return_value = FakeKey(directory), data.bucket_origin_file_name
        fake_add_update_date_to_json.return_value = data.json_output_return_example_string
        self.jats.emit_monitor_event = mock.MagicMock()
        self.jats.set_dashboard_properties = mock.MagicMock()

        success = self.jats.do_activity(testdata.ExpandArticle_data)
        self.assertDictEqual.__self__.maxDiff = None
        self.assertEqual(success, True)
        output_json = json.loads(directory.read("test_dest.json"))
        expected = data.json_output_return_example
        self.assertDictEqual(output_json, expected)

if __name__ == '__main__':
    unittest.main()
