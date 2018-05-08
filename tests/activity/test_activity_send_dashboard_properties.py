import unittest
import os
from activity.activity_SendDashboardProperties import activity_SendDashboardProperties
import settings_mock
from mock import patch, ANY
from tests.activity.classes_mock import FakeSession, FakeS3Connection, FakeKey, FakeLogger
from testfixtures import TempDirectory, tempdir
import test_activity_data as test_data


class TestSendDashboardEvents(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.send_dashboard_properties = activity_SendDashboardProperties(
            settings_mock, fake_logger, None, None, None)
        self.directory = TempDirectory()

    def tearDown(self):
        self.directory.cleanup()
        TempDirectory.cleanup_all()

    @tempdir()
    @patch.object(activity_SendDashboardProperties, 'emit_monitor_event')
    @patch('activity.activity_SendDashboardProperties.get_article_xml_key')
    @patch('activity.activity_SendDashboardProperties.S3Connection')
    @patch('activity.activity_SendDashboardProperties.get_session')
    @patch.object(activity_SendDashboardProperties, 'set_monitor_property')
    def test_do_activity(self, fake_emit_monitor_property, fake_session, fake_s3_mock, fake_get_article_xml_key,
                         fake_emit_monitor_event):

        fake_session.return_value = FakeSession(test_data.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        fake_get_article_xml_key.return_value = FakeKey(self.directory), test_data.bucket_origin_file_name

        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

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

        self.directory.cleanup()


    @tempdir()
    @patch.object(activity_SendDashboardProperties, 'emit_monitor_event')
    @patch('activity.activity_SendDashboardProperties.get_article_xml_key')
    @patch('activity.activity_SendDashboardProperties.S3Connection')
    @patch('activity.activity_SendDashboardProperties.get_session')
    @patch.object(activity_SendDashboardProperties, 'set_monitor_property')
    def test_do_activity_failure_no_xml(self, fake_emit_monitor_property, fake_session, fake_s3_mock, fake_get_article_xml_key,
                         fake_emit_monitor_event):
        "test if no XML file is supplied, will fail"
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        fake_get_article_xml_key.return_value = None, None

        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

        self.assertEqual(result, self.send_dashboard_properties.ACTIVITY_PERMANENT_FAILURE)

        self.directory.cleanup()


    @tempdir()
    @patch.object(activity_SendDashboardProperties, 'emit_monitor_event')
    @patch('activity.activity_SendDashboardProperties.get_article_xml_key')
    @patch('activity.activity_SendDashboardProperties.S3Connection')
    @patch('activity.activity_SendDashboardProperties.get_session')
    @patch.object(activity_SendDashboardProperties, 'set_monitor_property')
    def test_do_activity_failure_invalid_xml(self, fake_emit_monitor_property, fake_session, fake_s3_mock, fake_get_article_xml_key,
                         fake_emit_monitor_event):
        "test if XML fails to parse, here an incorrect pub_date, will fail"
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_s3_mock.return_value = FakeS3Connection()
        with open(os.path.join('tests', 'files_source', 'elife-00353-v1_bad_pub_date.xml')) as open_file:
            fake_get_article_xml_key.return_value = (
                FakeKey(self.directory, 'elife-00353-v1.xml', open_file.read()),
                test_data.bucket_origin_file_name)

        result = self.send_dashboard_properties.do_activity(test_data.dashboard_data)

        self.assertEqual(result, self.send_dashboard_properties.ACTIVITY_PERMANENT_FAILURE)

        self.directory.cleanup()


if __name__ == '__main__':
    unittest.main()
