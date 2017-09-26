import unittest
from activity.activity_ScheduleCrossref import activity_ScheduleCrossref
from activity.activity_ConvertJATS import activity_ConvertJATS as ConvertJATS
from mock import mock, patch
from tests.activity.classes_mock import FakeSession
from tests.activity.classes_mock import FakeKey
from tests.activity.classes_mock import FakeS3Connection
from tests.activity.classes_mock import FakeLogger
import tests.activity.settings_mock as settings_mock
import tests.activity.test_activity_data as testdata
from ddt import ddt, data, unpack


@ddt
class TestScheduleCrossref(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_ScheduleCrossref(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        pass

    @patch.object(activity_ScheduleCrossref, 'copy_article_xml_to_crossref_outbox')
    @patch.object(ConvertJATS, 'get_article_xml_key')
    @patch('activity.activity_ScheduleCrossref.S3Connection')
    @patch('activity.activity_ScheduleCrossref.Session')
    @patch.object(activity_ScheduleCrossref, 'emit_monitor_event')
    @patch.object(activity_ScheduleCrossref, 'set_monitor_property')
    @data(
        ('key_name', 'tests/test_data/elife-00353-v1.xml', True),
        (None, None, False),
        )
    @unpack
    def test_do_activity(self, xml_key, xml_filename, expected_result,
                         mock_set_monitor_property, mock_emit_monitor_event, fake_session_mock,
                         fake_s3_mock, fake_get_article_xml_key, fake_copy_article_xml):
        fake_session_mock.return_value = FakeSession(testdata.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        fake_copy_article_xml = mock.MagicMock()
        # create a fake Key if specified
        if xml_key:
            fake_key = FakeKey
            fake_key.name = xml_key
        else:
            fake_key = None
        fake_get_article_xml_key.return_value = (fake_key, xml_filename)

        result = self.activity.do_activity(testdata.ExpandArticle_data)
        self.assertEqual(result, expected_result)

    @data(
        ('crossref/outbox/', 'elife', '00353', 'crossref/outbox/elife00353.xml'),
        ('crossref/outbox/', 'elife', None, None),
        )
    @unpack
    def test_new_crossref_xml_name(self, prefix, journal, article_id, expected_result):
        self.assertEqual(
            self.activity.new_crossref_xml_name(prefix, journal, article_id), expected_result)


if __name__ == '__main__':
    unittest.main()
