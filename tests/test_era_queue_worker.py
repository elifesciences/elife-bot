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
    FakeSQSClient,
    FakeSQSQueue,
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
    @patch("boto3.client")
    def test_work(self, fake_sqs_client, mock_requests_head):
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
        fake_queue_messages = [
            {"Messages": [{"Body": json.dumps(self.incoming_message_body_json)}]}
        ]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.era_incoming_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
            settings_mock.workflow_starter_queue: FakeSQSQueue(directory),
        }
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # status code 404 means it does not yet exist and it will be deposited
        mock_requests_head.return_value = FakeResponse(404)

        # create a fake green flag
        flag = FakeFlag()

        # invoke queue worker to work
        self.queue_worker.work(flag)

        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(directory.read("fake_sqs_body"))
        self.assertEqual(out_queue_message, outgoing_message_expected)

    @patch("boto3.client")
    def test_work_bad_message_body(self, fake_sqs_client):
        "test if the incoming message body cannot be parsed into JSON"
        message_body = '{"not": "good" "json": "this JSON has no commas"}'

        # mock things
        directory = TempDirectory()
        fake_queue_messages = [{"Messages": [{"Body": message_body}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.era_incoming_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
        }
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # create a fake green flag
        flag = FakeFlag()

        # invoke queue worker to work
        self.queue_worker.work(flag)

        # assert exception is printed in the log
        self.assertEqual(
            self.logger.logexception,
            (
                "Exception loading message body as JSON: "
                + str(message_body)
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
