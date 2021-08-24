import unittest
import json

from mock import patch
from testfixtures import TempDirectory
from era_queue_worker import EraQueueWorker
from tests import settings_mock
from tests.classes_mock import FakeFlag
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSQSConn,
    FakeSQSMessage,
)


class TestEraQueueWorker(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.queue_worker = EraQueueWorker(settings_mock, self.logger)
        # override the wait value for faster testing
        self.queue_worker.wait_time_seconds = 1

        self.article_id = "30274"
        self.display = "https://elife.stencila.io/article-30274/"
        self.download = "https://hub.stenci.la/api/projects/518/snapshots/15/archive"

        self.incoming_message_body_json = {
            "id": self.article_id,
            "date": "2020-08-24T13:30:00Z",
            "display": self.display,
            "download": self.download,
        }

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.head")
    @patch("era_queue_worker.Message")
    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("boto.sqs.connect_to_region")
    def test_work(
        self, fake_sqs_conn, fake_queue_read, fake_sqs_message, mock_requests_head
    ):
        "test the main method of the class"
        outgoing_message_expected = {
            "workflow_name": "SoftwareHeritageDeposit",
            "workflow_data": {
                "run": None,
                "info": {
                    "article_id": self.article_id,
                    "version": "1",
                    "workflow": "software_heritage",
                    "recipient": "software_heritage",
                    "input_file": self.download,
                    "data": {"display": self.display},
                },
            },
        }

        # mock things
        directory = TempDirectory()
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        fake_sqs_message.return_value = FakeSQSMessage(directory)

        incoming_message = FakeSQSMessage(directory)
        incoming_message.set_body(json.dumps(self.incoming_message_body_json))
        fake_queue_read.return_value = incoming_message

        # status code 404 means it does not yet exist and it will be deposited
        mock_requests_head.return_value = FakeResponse(404)

        # create a fake green flag
        flag = FakeFlag()

        # invoke queue worker to work
        self.queue_worker.work(flag)

        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(directory.read("fake_sqs_body"))
        self.assertEqual(out_queue_message, outgoing_message_expected)

    @patch("era_queue_worker.Message")
    @patch("tests.activity.classes_mock.FakeSQSQueue.read")
    @patch("boto.sqs.connect_to_region")
    def test_work_bad_message_body(
        self, fake_sqs_conn, fake_queue_read, fake_sqs_message
    ):
        "test if the incoming message body cannot be parsed into JSON"
        message_body = '{"not": "good" "json": "this JSON has no commas"}'
        # expected queue message will be similar to the incoming message,
        # since it does not result in an outgoing message to the workflow starter queue
        queue_message_expected = bytes(message_body, "utf8")

        # mock things
        directory = TempDirectory()
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        fake_sqs_message.return_value = FakeSQSMessage(directory)

        incoming_message = FakeSQSMessage(directory)
        incoming_message.set_body(message_body)
        fake_queue_read.return_value = incoming_message

        # create a fake green flag
        flag = FakeFlag()

        # invoke queue worker to work
        self.queue_worker.work(flag)

        # assertions, there is no workflow starter message out_queue
        out_queue_message = directory.read("fake_sqs_body")
        self.assertEqual(out_queue_message, queue_message_expected)
        # and exception is printed in the log
        self.assertEqual(
            self.logger.logexception,
            (
                "Exception loading message body as JSON: "
                + str(queue_message_expected)
                + ": Expecting ',' delimiter: line 1 column 16 (char 15)"
            ),
        )

    @patch("requests.head")
    def test_approve_workflow_start_200(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(200)
        self.assertEqual(
            self.queue_worker.approve_workflow_start("https://example.org"), False
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "Origin https://example.org already exists at Software Heritage",
        )

    @patch("requests.head")
    def test_approve_workflow_start_404(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(404)
        self.assertEqual(
            self.queue_worker.approve_workflow_start("https://example.org"), True
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "Origin https://example.org does not exist yet at Software Heritage",
        )

    @patch("requests.head")
    def test_approve_workflow_start_500(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(500)
        self.assertEqual(
            self.queue_worker.approve_workflow_start("https://example.org"), False
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "Could not determine the status of the origin https://example.org",
        )

    @patch("requests.head")
    def test_approve_workflow_start_exception(self, mock_requests_head):
        mock_requests_head.side_effect = Exception("An exception")
        self.assertEqual(
            self.queue_worker.approve_workflow_start("https://example.org"), False
        )
        self.assertEqual(
            self.logger.logexception,
            "Exception when checking swh_origin_exists for origin https://example.org",
        )
