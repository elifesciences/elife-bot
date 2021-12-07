import unittest
from mock import patch
from activity.activity_VerifyGlencoe import activity_VerifyGlencoe
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import (
    FakeResponse,
    FakeSession,
    FakeStorageContext,
    FakeLogger,
)
import tests.activity.test_activity_data as test_data


class TestVerifyGlencoe(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.verifyglencoe = activity_VerifyGlencoe(
            settings_mock, self.logger, None, None, None
        )

    @patch("provider.glencoe_check.validate_sources")
    @patch("provider.glencoe_check.metadata")
    @patch("provider.glencoe_check.has_videos")
    @patch("provider.glencoe_check.check_msid")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_VerifyGlencoe.storage_context")
    @patch("activity.activity_VerifyGlencoe.get_session")
    @patch.object(activity_VerifyGlencoe, "emit_monitor_event")
    def test_do_acitvity_has_videos(
        self,
        fake_emit_monitor,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
        fake_check_msid,
        fake_has_videos,
        fake_metadata,
        fake_validate_sources,
    ):
        """test for a successful result if has videos"""
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = "anything.xml"
        fake_check_msid.return_value = test_data.session_example.get("article_id")
        fake_metadata.return_value = {}
        fake_has_videos.return_value = True
        fake_validate_sources.return_value = True
        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)
        self.assertTrue(result)

    @patch("provider.glencoe_check.has_videos")
    @patch("provider.glencoe_check.check_msid")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_VerifyGlencoe.storage_context")
    @patch("activity.activity_VerifyGlencoe.get_session")
    @patch.object(activity_VerifyGlencoe, "emit_monitor_event")
    def test_do_acitvity_no_videos(
        self,
        fake_emit_monitor,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
        fake_check_msid,
        fake_has_videos,
    ):
        """test for a successful result if article does not have videos"""
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = "anything.xml"
        fake_check_msid.return_value = test_data.session_example.get("article_id")
        fake_has_videos.return_value = False
        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)
        self.assertTrue(result)

    @patch("time.sleep")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_VerifyGlencoe.storage_context")
    @patch("activity.activity_VerifyGlencoe.get_session")
    @patch.object(activity_VerifyGlencoe, "emit_monitor_event")
    @patch("requests.get")
    def test_do_activity_bad_response_glencoe_404(
        self,
        request_mock,
        fake_emit_monitor,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
        fake_sleep,
    ):
        session_example = {
            "version": "1",
            "article_id": "7777777701234",
            "run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
            "expanded_folder": "7777777701234.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
            "update_date": "2012-12-13T00:00:00Z",
            "file_name": "elife-7777777701234-vor-v1.zip",
            "filename_last_element": "elife-7777777701234-vor-r1.zip",
        }
        request_mock.return_value = FakeResponse(404, None)
        fake_session.return_value = FakeSession(session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_sleep.return_value = True
        fake_get_xml_file_name.return_value = "anything.xml"

        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)
        fake_emit_monitor.assert_called_with(
            settings_mock,
            session_example["article_id"],
            session_example["version"],
            session_example["run"],
            self.verifyglencoe.pretty_name,
            "error",
            "Glencoe video is not available for article 7777777701234; message: "
            "article has no videos - url requested: 10.7554/eLife.01234",
        )
        self.assertEqual(result, self.verifyglencoe.ACTIVITY_TEMPORARY_FAILURE)

    @patch("time.sleep")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_VerifyGlencoe.storage_context")
    @patch("activity.activity_VerifyGlencoe.get_session")
    @patch.object(activity_VerifyGlencoe, "emit_monitor_event")
    @patch("requests.get")
    def test_do_activity_bad_response_glencoe_500(
        self,
        request_mock,
        fake_emit_monitor,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
        fake_sleep,
    ):
        request_mock.return_value = FakeResponse(500, None)
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_sleep.return_value = True
        fake_get_xml_file_name.return_value = "anything.xml"

        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)
        fake_emit_monitor.assert_called_with(
            settings_mock,
            test_data.session_example["article_id"],
            test_data.session_example["version"],
            test_data.ExpandArticle_data["run"],
            self.verifyglencoe.pretty_name,
            "error",
            "Glencoe video is not available for article 353; message: "
            "unhandled status code from Glencoe: 500 - "
            "url requested: 10.7554/eLife.00353",
        )
        self.assertEqual(result, self.verifyglencoe.ACTIVITY_TEMPORARY_FAILURE)

    @patch("provider.glencoe_check.metadata")
    @patch("provider.glencoe_check.validate_sources")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch("activity.activity_VerifyGlencoe.storage_context")
    @patch("activity.activity_VerifyGlencoe.get_session")
    @patch.object(activity_VerifyGlencoe, "emit_monitor_event")
    def test_do_acitvity_exception(
        self,
        fake_emit_monitor,
        fake_session,
        fake_storage_context,
        fake_get_xml_file_name,
        fake_glencoe_check_validate_sources,
        fake_glencoe_check_metadata,
    ):
        fake_session.return_value = FakeSession(test_data.session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_glencoe_check_metadata.return_value = {}
        fake_get_xml_file_name.return_value = "anything.xml"

        fake_glencoe_check_validate_sources.side_effect = Exception("Fake Time out")

        result = self.verifyglencoe.do_activity(test_data.ExpandArticle_data)

        fake_emit_monitor.assert_called_with(
            settings_mock,
            test_data.session_example["article_id"],
            test_data.session_example["version"],
            test_data.ExpandArticle_data["run"],
            self.verifyglencoe.pretty_name,
            "error",
            "An error occurred when checking for Glencoe video. Article 353; message: "
            "Fake Time out",
        )

        self.assertEqual(result, self.verifyglencoe.ACTIVITY_PERMANENT_FAILURE)


if __name__ == "__main__":
    unittest.main()
