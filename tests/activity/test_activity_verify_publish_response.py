import unittest
from activity.activity_VerifyPublishResponse import activity_VerifyPublishResponse
from ddt import ddt, data
from mock import patch
import settings_mock

data_published_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "published",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
            "requested_action": "publish",
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        }

data_published_website = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
            "update_date": "2012-12-13T00:00:00Z"
        }
data_error_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "error",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
            "requested_action": "publish",
            "message": "An error abc has occurred",
            "update_date": "2012-12-13T00:00:00Z"
        }

@ddt
class TestVerifyPublishResponse(unittest.TestCase):
    def setUp(self):
        self.verifypublishresponse = activity_VerifyPublishResponse(settings_mock, None, None, None, None)

    @data(data_published_lax)
    def test_get_events_data_published_lax(self, data):
        (exp_start_msg, exp_end_msg, exp_result) = self.verifypublishresponse.get_events(data, "Journal")
        self.assertEqual(exp_start_msg, [settings_mock, data["article_id"], data["version"],
                                         data["run"], self.verifypublishresponse.pretty_name + ": Journal", "start",
                                         "Starting verification of Publish response " + data["article_id"]])
        self.assertEqual(exp_end_msg, [settings_mock, data["article_id"], data["version"],
                                       data["run"], self.verifypublishresponse.pretty_name + ": Journal", "end",
                                       " Finished Verification. Lax has responded with result: published."
                                       " Article: " + data["article_id"]])
        self.assertEqual(exp_result, self.verifypublishresponse.ACTIVITY_SUCCESS)

    @data(data_published_lax)
    @patch.object(activity_VerifyPublishResponse, 'publication_authority')
    @patch.object(activity_VerifyPublishResponse, 'emit_monitor_event')
    def test_do_activity_data_published_lax(self, data, fake_emit_monitor, fake_publication_authority):
        fake_publication_authority.return_value = "Journal"
        result = self.verifypublishresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             self.verifypublishresponse.pretty_name + ": Journal",
                                             "end",
                                             " Finished Verification. Lax has responded with result: published."
                                             " Article: " + data["article_id"])
        self.assertEqual(result, self.verifypublishresponse.ACTIVITY_SUCCESS)

    @data(data_error_lax)
    @patch.object(activity_VerifyPublishResponse, 'publication_authority')
    @patch.object(activity_VerifyPublishResponse, 'emit_monitor_event')
    def test_do_activity_data_error_lax(self, data, fake_emit_monitor, fake_publication_authority):
        fake_publication_authority.return_value = "Journal"
        result = self.verifypublishresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             self.verifypublishresponse.pretty_name + ": Journal",
                                             "error",
                                             " Lax has not published article " + data["article_id"] +
                                             " result from lax:" + str(data['result']) + '; message from lax: ' +
                                             data['message'])
        self.assertEqual(result, self.verifypublishresponse.ACTIVITY_PERMANENT_FAILURE)

    @data(data_published_website)
    @patch.object(activity_VerifyPublishResponse, 'publication_authority')
    @patch.object(activity_VerifyPublishResponse, 'emit_monitor_event')
    def test_do_activity_data_published_journal(self, data, fake_emit_monitor, fake_publication_authority):
        fake_publication_authority.return_value = "elife-website"
        result = self.verifypublishresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             self.verifypublishresponse.pretty_name + ": elife-website",
                                             "end",
                                             "Finished verification of Publish response " + data["article_id"])
        self.assertEqual(result, self.verifypublishresponse.ACTIVITY_SUCCESS)

    @data(data_error_lax)
    @patch.object(activity_VerifyPublishResponse, 'publication_authority')
    @patch.object(activity_VerifyPublishResponse, 'emit_monitor_event')
    def test_do_activity_data_error_published_journal_publ_authority_website(self, data, fake_emit_monitor, fake_publication_authority):
        fake_publication_authority.return_value = "elife-website"
        result = self.verifypublishresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             self.verifypublishresponse.pretty_name + ": Journal",
                                             "error",
                                             " Lax has not published article " + data["article_id"] +
                                             " We will exit this workflow as the publication authority is"
                                             " elife-website."
                                             " result from lax:" + data['result'] + '; message from lax: ' +
                                             data['message'])
        self.assertEqual(result, self.verifypublishresponse.ACTIVITY_PERMANENT_FAILURE)

    @data(data_published_lax)
    @patch.object(activity_VerifyPublishResponse, 'publication_authority')
    @patch.object(activity_VerifyPublishResponse, 'emit_monitor_event')
    def test_do_activity_data_published_journal_publ_authority_website(self, data, fake_emit_monitor, fake_publication_authority):
        fake_publication_authority.return_value = "elife-website"
        result = self.verifypublishresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             self.verifypublishresponse.pretty_name + ": Journal",
                                             "end",
                                             " Finished Verification. Lax has responded with result: published."
                                             " Authority: elife-website. Exiting."
                                             " Article: " + data["article_id"])
        self.assertEqual(result, self.verifypublishresponse.ACTIVITY_EXIT_WORKFLOW)


if __name__ == '__main__':
    unittest.main()
