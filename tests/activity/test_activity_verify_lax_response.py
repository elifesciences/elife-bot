import unittest
from activity.activity_VerifyLaxResponse import activity_VerifyLaxResponse
import activity
import settings_mock
from classes_mock import FakeSession
from ddt import ddt, data
from mock import patch


def fake_emit_monitor_event(settings, item_identifier, version, run, event_type, status, message):
    pass

@ddt
class TestVerifyLaxResponse(unittest.TestCase):
    def setUp(self):
        self.verifylaxresponse = activity_VerifyLaxResponse(settings_mock, None, None, None, None)

    @data({
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "ingested",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "ingest",
            "force": False,
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        })
    @patch('activity.activity_VerifyLaxResponse.get_session')
    @patch.object(activity_VerifyLaxResponse, 'emit_monitor_event')
    def test_do_activity(self, data, fake_emit_monitor, fake_get_session):
        fake_emit_monitor.side_effect = fake_emit_monitor_event
        fake_session = FakeSession({})
        fake_get_session.return_value = fake_session
        result = self.verifylaxresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             "Verify Lax Response",
                                             "end",
                                             " Finished Verification. Lax has responded with result: ingested."
                                             " Article: " + data["article_id"])
        self.assertEqual(result, self.verifylaxresponse.ACTIVITY_SUCCESS)
        self.assertEqual(fake_session.get_value('published'), False)


    @data({
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "ingested",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "ingest",
            "force": True,
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        })
    @patch('activity.activity_VerifyLaxResponse.get_session')
    @patch.object(activity_VerifyLaxResponse, 'emit_monitor_event')
    def test_do_activity_force_true(self, data, fake_emit_monitor, fake_get_session):
        fake_emit_monitor.side_effect = fake_emit_monitor_event
        fake_session = FakeSession({})
        fake_get_session.return_value = fake_session
        result = self.verifylaxresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             "Verify Lax Response",
                                             "end",
                                             " Finished Verification. Lax has responded with result: ingested."
                                             " Article: " + data["article_id"])
        self.assertEqual(result, self.verifylaxresponse.ACTIVITY_SUCCESS)
        self.assertEqual(fake_session.get_value('published'), True)


    @data({
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "error",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "ingest",
            "force": False,
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        })
    @patch('activity.activity_VerifyLaxResponse.get_session')
    @patch.object(activity_VerifyLaxResponse, 'emit_monitor_event')
    def test_do_activity_error_no_message(self, data, fake_emit_monitor, fake_session):
        fake_emit_monitor.side_effect = fake_emit_monitor_event
        fake_session.return_value = FakeSession({})
        result = self.verifylaxresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             "Verify Lax Response",
                                             "error",
                                             "Lax has not ingested article " + data["article_id"] +
                                             " result from lax:" + str(data['result']) + '; message from lax: ' + "(empty message)")
        self.assertEqual(result, self.verifylaxresponse.ACTIVITY_PERMANENT_FAILURE)

    @data({
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "error",
            "status": "poa",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "ingest",
            "force": False,
            "message": "An error has occurred",
            "update_date": "2012-12-13T00:00:00Z"
        })
    @patch('activity.activity_VerifyLaxResponse.get_session')
    @patch.object(activity_VerifyLaxResponse, 'emit_monitor_event')
    def test_do_activity_error(self, data, fake_emit_monitor, fake_session):
        fake_emit_monitor.side_effect = fake_emit_monitor_event
        fake_session.return_value = FakeSession({})
        result = self.verifylaxresponse.do_activity(data)
        fake_emit_monitor.assert_called_with(settings_mock,
                                             data["article_id"],
                                             data["version"],
                                             data["run"],
                                             "Verify Lax Response",
                                             "error",
                                             "Lax has not ingested article " + data["article_id"] +
                                             " result from lax:" + str(data['result']) + '; message from lax: ' + data["message"])
        self.assertEqual(result, self.verifylaxresponse.ACTIVITY_PERMANENT_FAILURE)




if __name__ == '__main__':
    unittest.main()
