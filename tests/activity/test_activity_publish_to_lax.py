import unittest
import copy
import json
from ddt import ddt, data
from mock import patch
from provider.utils import base64_encode_string, base64_decode_string
from activity.activity_PublishToLax import activity_PublishToLax as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSQSConn,
    FakeSQSQueue,
    FakeSQSMessage,
)
from testfixtures import TempDirectory


ACTIVITY_DATA = {
    "article_id": "353",
    "version": "1",
    "run": "bb2d37b8-e73c-43b3-a092-d555753316af",
    "status": "vor",
    "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
}


WORKFLOW_DATA = {
    "workflow_data": {
        "article_id": u"353",
        "expanded_folder": u"00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
        "message": None,
        "requested_action": u"publish",
        "force": False,
        "result": u"published",
        "run": u"bb2d37b8-e73c-43b3-a092-d555753316af",
        "status": u"vor",
        "update_date": "2013-03-26T00:00:00Z",
        "version": u"1",
        "run_type": None,
    }
}


def workflow_data(data, run_type=None):
    "format workflow data for different test scenarios"
    workflow_data = copy.copy(data)
    if run_type:
        workflow_data["run_type"] = run_type
    return workflow_data


def activity_data(data, force=None, workflow_data=None):
    "format activity data for different test scenarios"
    activity_data = copy.copy(data)
    if force:
        activity_data["force"] = force
    if workflow_data:
        activity_data["publication_data"] = base64_encode_string(
            json.dumps(workflow_data)
        )
    return activity_data


@ddt
class TestPublishToLax(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("activity.activity_PublishToLax.RawMessage")
    @patch("boto.sqs.connection.SQSConnection.get_queue")
    @patch("boto.sqs.connect_to_region")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch.object(activity_object, "emit_monitor_event")
    @data(
        {"comment": "default activity input data", "expected_force": False},
        {"comment": "test force is True", "force": True, "expected_force": True},
        {
            "comment": "test with default workflow data",
            "set_workflow_data": True,
            "expected_force": False,
        },
        {
            "comment": "test workflow data with run_type",
            "set_workflow_data": True,
            "run_type": "silent-correction",
            "expected_force": False,
        },
    )
    def test_do_activity_success(
        self,
        test_data,
        fake_emit,
        fake_file_name,
        fake_sqs_conn,
        fake_sqs_queue,
        fake_sqs_message,
    ):
        directory = TempDirectory()
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        fake_sqs_queue.return_value = FakeSQSQueue(directory)
        fake_sqs_message.return_value = FakeSQSMessage(directory)
        fake_file_name.return_value = "elife-00353-v1.xml"
        # format the activity data
        workflow_test_data = None
        if test_data.get("set_workflow_data"):
            workflow_test_data = workflow_data(WORKFLOW_DATA, test_data.get("run_type"))
        activity_test_data = activity_data(
            ACTIVITY_DATA, test_data.get("force"), workflow_test_data
        )
        # run do_activity
        result = self.activity.do_activity(activity_test_data)
        # make assertions
        self.assertEqual(result, True)
        # read in the message body from the TempDirectory()
        message_body = json.loads(directory.read("fake_sqs_body").decode())
        self.assertEqual(message_body.get("force"), test_data.get("expected_force"))
        self.assertEqual(message_body.get("action"), "publish")
        self.assertEqual(message_body.get("id"), activity_test_data.get("article_id"))
        self.assertIsNotNone(message_body.get("location"))
        # parse the token
        token = json.loads(base64_decode_string(message_body.get("token")))
        self.assertEqual(token.get("status"), activity_test_data.get("status"))
        self.assertEqual(token.get("run_type"), activity_test_data.get("run_type"))
        self.assertEqual(token.get("force"), test_data.get("expected_force"))
        self.assertEqual(
            token.get("expanded_folder"), activity_test_data.get("expanded_folder")
        )
        self.assertEqual(token.get("version"), activity_test_data.get("version"))
        self.assertEqual(token.get("run"), activity_test_data.get("run"))

    @patch("provider.lax_provider.prepare_action_message")
    @patch.object(activity_object, "emit_monitor_event")
    def test_do_activity_error(self, fake_emit, fake_lax_provider):
        fake_lax_provider.side_effect = Exception("Access Denied")
        result = self.activity.do_activity(activity_data(ACTIVITY_DATA))
        self.assertEqual(result, False)


if __name__ == "__main__":
    unittest.main()
