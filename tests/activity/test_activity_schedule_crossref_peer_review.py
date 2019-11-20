import unittest
import os
import copy
import shutil
from mock import mock, patch
import activity.activity_ScheduleCrossrefPeerReview as activity_module
from activity.activity_ScheduleCrossrefPeerReview import (
    activity_ScheduleCrossrefPeerReview as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


class TestScheduleCrossrefPeerReview(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch('provider.lax_provider.article_highest_version')
    @patch('provider.article.storage_context')
    @patch.object(activity_module, 'storage_context')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_object, 'xml_sub_article_exists')
    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity(self, fake_emit_monitor,
                         fake_sub_article_exists, fake_session_mock,
                         fake_storage_context, fake_article_storage_context, fake_highest_version):
        expected_result = True
        fake_session_mock.return_value = FakeSession(activity_test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_article_storage_context.return_value = FakeStorageContext()
        fake_highest_version.return_value = 1
        fake_sub_article_exists.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch('provider.lax_provider.article_highest_version')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity_silent_correction(self, fake_emit_monitor,
                                           fake_session_mock, fake_highest_version):
        expected_result = True
        session_dict = copy.copy(activity_test_data.session_example)
        session_dict['run_type'] = 'silent-correction'
        fake_session_mock.return_value = FakeSession(session_dict)
        fake_highest_version.return_value = 2
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(result, expected_result)
        self.assertEqual(self.activity.logger.loginfo, (
            'ScheduleCrossrefPeerReview will not deposit article 00353 ingested by'
            ' silent-correction, its version of 1 does not equal the highest version which is 2'))

    @patch('provider.lax_provider.article_highest_version')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_object, 'xml_sub_article_exists')
    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity_no_sub_article(self, fake_emit_monitor, fake_sub_article_exists,
                                        fake_session_mock, fake_highest_version):
        expected_result = True
        fake_sub_article_exists.return_value = False
        fake_session_mock.return_value = FakeSession(activity_test_data.session_example)
        fake_highest_version.return_value = 1
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(result, expected_result)
        self.assertEqual(self.activity.logger.loginfo, (
            'ScheduleCrossrefPeerReview finds version 1 of 00353 has no sub-article'
            ' for peer review depositing'))

    @patch('provider.lax_provider.get_xml_file_name')
    @patch('provider.lax_provider.article_highest_version')
    @patch.object(activity_module, 'get_session')
    @patch.object(activity_object, 'xml_sub_article_exists')
    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity_exception(self, fake_emit_monitor,
                                   fake_sub_article_exists, fake_session_mock,
                                   fake_highest_version, fake_get_xml_file_name):
        expected_result = False
        fake_sub_article_exists.return_value = True
        fake_get_xml_file_name.side_effect = Exception("Something went wrong!")
        fake_session_mock.return_value = FakeSession(activity_test_data.session_example)
        fake_highest_version.return_value = 1
        # do the activity
        result = self.activity.do_activity(activity_test_data.data_example_before_publish)
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, 'download_jats')
    def test_xml_sub_article_exists(self, fake_download_jats):
        file_name = 'elife-15747-v2.xml'
        source_file = 'tests/test_data/crossref_peer_review/outbox/' + file_name
        dest_file = os.path.join(self.activity.get_tmp_dir(), file_name)
        shutil.copy(source_file, dest_file)
        fake_download_jats.return_value = dest_file
        self.assertTrue(self.activity.xml_sub_article_exists(''))

    @patch.object(activity_module, 'download_jats')
    def test_xml_sub_article_exists_not(self, fake_download_jats):
        file_name = 'elife-00353-v1.xml'
        source_file = 'tests/files_source/' + file_name
        dest_file = os.path.join(self.activity.get_tmp_dir(), file_name)
        shutil.copy(source_file, dest_file)
        fake_download_jats.return_value = dest_file
        self.assertFalse(self.activity.xml_sub_article_exists(''))


if __name__ == '__main__':
    unittest.main()
