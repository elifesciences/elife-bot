import unittest
import json
from ddt import ddt, data
from mock import patch
from testfixtures import TempDirectory
import activity.activity_IngestToLax as activity_module
from activity.activity_IngestToLax import activity_IngestToLax
from tests.activity import settings_mock
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeSQSQueue,
    FakeSQSClient,
)
from tests.activity import test_activity_data


data_example = {
    "article_id": "353",
    "update_date": "2016-10-05T10:31:54Z",
    "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
    "message": None,
    "requested_action": "ingest",
    "result": "ingested",
    "run": "bb2d37b8-e73c-43b3-a092-d555753316af",
    "status": "vor",
    "version": "1",
    "run_type": "initial-article",
}


@ddt
class TestIngestToLax(unittest.TestCase):
    def setUp(self):
        self.ingesttolax = activity_IngestToLax(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()

    @data(data_example)
    @patch("boto3.client")
    @patch("provider.lax_provider.get_xml_file_name")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_IngestToLax, "emit_monitor_event")
    def test_do_activity_success(
        self,
        test_data,
        fake_emit_monitor,
        fake_session,
        fake_xml_file_name,
        fake_sqs_client,
    ):
        directory = TempDirectory()

        # mock the SQS client and queues
        fake_queues = {
            settings_mock.xml_info_queue: FakeSQSQueue(directory),
        }
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        fake_session.return_value = FakeSession(
            test_activity_data.data_example_before_publish
        )
        fake_xml_file_name.return_value = "elife-00353-v1.xml"

        return_value = self.ingesttolax.do_activity(test_data)
        self.assertEqual(return_value, activity_IngestToLax.ACTIVITY_SUCCESS)
        out_queue_message = json.loads(directory.read("fake_sqs_body"))
        self.assertEqual(out_queue_message.get("action"), "ingest")
        self.assertEqual(out_queue_message.get("id"), test_data.get("article_id"))
        self.assertEqual(
            out_queue_message.get("version"), int(test_data.get("version"))
        )
        self.assertEqual(out_queue_message.get("force"), False)

    @patch.object(activity_IngestToLax, "get_message_queue")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_IngestToLax, "emit_monitor_event")
    def test_do_activity_error(
        self, fake_emit_monitor, fake_session, fake_message_queue
    ):
        """test for when the end_event is error"""
        fake_data = {"run": ""}
        start_event = []
        end_event = "error"
        fake_message_queue.return_value = None, None, start_event, end_event, None, None
        return_value = self.ingesttolax.do_activity(fake_data)
        self.assertEqual(return_value, activity_IngestToLax.ACTIVITY_PERMANENT_FAILURE)

    @data(data_example)
    @patch("provider.lax_provider.prepare_action_message")
    def test_get_message_queue_success(self, data, fake_action_message):
        fake_action_message.return_value = {"example_message": True}

        (
            message,
            queue,
            start_event,
            end_event,
            end_event_details,
            exception,
        ) = self.ingesttolax.get_message_queue(data)
        self.assertEqual(queue, settings_mock.xml_info_queue)
        self.assertEqual(
            start_event,
            [
                settings_mock,
                data["article_id"],
                data["version"],
                data["run"],
                self.ingesttolax.pretty_name,
                "start",
                "Starting preparation of article for Lax " + data["article_id"],
            ],
        )
        self.assertEqual(end_event, "end")
        self.assertEqual(
            end_event_details,
            [
                settings_mock,
                data["article_id"],
                data["version"],
                data["run"],
                self.ingesttolax.pretty_name,
                "end",
                "Finished preparation of article for Lax. "
                "Ingest sent to Lax" + data["article_id"],
            ],
        )
        self.assertIsNone(exception)

    @data(data_example)
    @patch("provider.lax_provider.prepare_action_message")
    def test_get_message_queue_error(self, data, fake_lax_provider):
        fake_lax_provider.side_effect = Exception("Access Denied")
        (
            message,
            queue,
            start_event,
            end_event,
            end_event_details,
            exception,
        ) = self.ingesttolax.get_message_queue(data)
        self.assertEqual(end_event, "error")
        self.assertEqual(exception, "Access Denied")
        self.assertListEqual(
            end_event_details,
            [
                settings_mock,
                data["article_id"],
                data["version"],
                data["run"],
                self.ingesttolax.pretty_name,
                "error",
                "Error preparing or sending message to lax"
                + data["article_id"]
                + " message: Access Denied",
            ],
        )


if __name__ == "__main__":
    unittest.main()
