import unittest
from activity.activity_SendDashboardProperties import activity_SendDashboardProperties
import settings_mock
from mock import patch, ANY
from classes_mock import FakeSession
from classes_mock import FakeS3Connection
from classes_mock import FakeKey
from testfixtures import TempDirectory
from testfixtures import tempdir
import test_activity_data as test_data


class TestSendDashboardEvents(unittest.TestCase):

    def setUp(self):

        self.send_dashboard_properties = activity_SendDashboardProperties(settings_mock, None, None, None, None)

    @tempdir()
    @patch.object(activity_SendDashboardProperties, 'emit_monitor_event')
    @patch('activity.activity_SendDashboardProperties.get_article_xml_key')
    @patch('activity.activity_SendDashboardProperties.S3Connection')
    @patch('activity.activity_SendDashboardProperties.Session')
    @patch.object(activity_SendDashboardProperties, 'set_monitor_property')
    def test_do_activity(self, fake_emit_monitor_property, fake_session, fake_s3_mock, fake_get_article_xml_key,
                         fake_emit_monitor_event):

        directory = TempDirectory()
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        fake_get_article_xml_key.return_value = FakeKey(directory), test_data.bucket_origin_file_name

        result = self.send_dashboard_properties.do_activity(test_data.ConvertJATS_data)

        self.assertEqual(result, True)

        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'doi', u'10.7554/eLife.00353', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'title', u'A good life', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'status', u'VOR', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'publication-date', u'2012-12-13', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'article-type', u'discussion', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'corresponding-authors', u'Eve Marder', 'text', version='1')
        fake_emit_monitor_property.assert_any_call(ANY, '00353', 'authors', u'Eve Marder', 'text', version='1')

        fake_emit_monitor_event.assert_any_call(ANY, '00353', '1', '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                                                'Send dashboard properties', 'start',
                                                'Starting send of article properties to dashboard for article 00353')
        fake_emit_monitor_event.assert_any_call(ANY, '00353', '1', '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                                                'Send dashboard properties', 'end',
                                                'Article properties sent to dashboard for article  00353')

        directory.cleanup()

if __name__ == '__main__':
    unittest.main()
