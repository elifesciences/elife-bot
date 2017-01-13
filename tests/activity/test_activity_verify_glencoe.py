import unittest
from activity.activity_VerifyGlencoe import activity_VerifyGlencoe
import settings_mock
from mock import patch, MagicMock
from classes_mock import FakeResponse
from classes_mock import FakeSession
from classes_mock import FakeStorageContext
import test_activity_data as test_data

class TestVerifyGlencoe(unittest.TestCase):

    def setUp(self):
        self.verifyglencoe = activity_VerifyGlencoe(settings_mock, None, None, None, None)

    def test_check_msid_long_id(self):
        result = self.verifyglencoe.check_msid("7777777701234")
        self.assertEqual('01234', result)

    def test_check_msdi_proper_id(self):
        result = self.verifyglencoe.check_msid("01234")
        self.assertEqual('01234', result)

    def test_check_msdi_short_id(self):
        result = self.verifyglencoe.check_msid("34")
        self.assertEqual('00034', result)

    @patch('time.sleep')
    @patch('provider.lax_provider.get_xml_file_name')
    @patch('activity.activity_VerifyGlencoe.StorageContext')
    @patch('activity.activity_VerifyGlencoe.Session')
    @patch.object(activity_VerifyGlencoe, 'emit_monitor_event')
    @patch('requests.get')
    def test_do_activity_bad_response_glencoe_404(self, request_mock, fake_emit_monitor, fake_session,
                                                  fake_storage_context, fake_get_xml_file_name, fake_sleep):
        request_mock.return_value = FakeResponse(404, None)
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = "anything.xml"
        self.verifyglencoe.logger = MagicMock()
        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             test_data.session_example["article_id"],
                                             test_data.session_example["version"],
                                             test_data.session_example["run"],
                                             self.verifyglencoe.pretty_name,
                                             "error",
                                             "Glencoe video is not available for article 00353; message: "
                                             "article has no videos")
        self.assertEqual(result, self.verifyglencoe.ACTIVITY_TEMPORARY_FAILURE)

    @patch('provider.glencoe_check.metadata')
    @patch('provider.glencoe_check.validate_sources')
    @patch('provider.lax_provider.get_xml_file_name')
    @patch('activity.activity_VerifyGlencoe.StorageContext')
    @patch('activity.activity_VerifyGlencoe.Session')
    @patch.object(activity_VerifyGlencoe, 'emit_monitor_event')
    def test_do_acitvity_exception(self, fake_emit_monitor, fake_session, fake_storage_context, fake_get_xml_file_name,
                                   fake_glencoe_check_validate_sources, fake_glencoe_check_metadata):
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = "anything.xml"

        self.verifyglencoe.logger = MagicMock()

        fake_glencoe_check_validate_sources.side_effect = Exception("Fake Time out")

        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)

        fake_emit_monitor.assert_called_with(settings_mock,
                                             test_data.session_example["article_id"],
                                             test_data.session_example["version"],
                                             test_data.session_example["run"],
                                             self.verifyglencoe.pretty_name,
                                             "error",
                                             "An error occurred when checking for Glencoe video. Article 00353; message: "
                                             "Fake Time out")

        self.assertEqual(result, self.verifyglencoe.ACTIVITY_PERMANENT_FAILURE)


if __name__ == '__main__':
    unittest.main()
