import unittest
import json
from mock import patch
from testfixtures import TempDirectory
from lax_response_adapter import LaxResponseAdapter, ShortRetryException
from provider.utils import base64_encode_string, bytes_decode
from tests import settings_mock, test_data
from tests.classes_mock import FakeFlag
from tests.activity.classes_mock import FakeLogger, FakeSQSClient, FakeSQSQueue


FAKE_TOKEN = json.dumps(
    {
        "status": "vor",
        "expanded_folder": "837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "version": "1",
        "force": False,
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
    }
)

FAKE_LAX_MESSAGE = json.dumps(
    {
        "status": "published",
        "requested-action": "publish",
        "datetime": "2013-03-26T00:00:00+00:00",
        "token": base64_encode_string(FAKE_TOKEN),
        "id": "837411455",
    }
)

WORKFLOW_MESSAGE_EXPECTED = {
    "workflow_data": {
        "article_id": "837411455",
        "expanded_folder": "837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "message": None,
        "requested_action": "publish",
        "force": False,
        "result": "published",
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "status": "vor",
        "update_date": "2013-03-26T00:00:00Z",
        "version": "1",
        "run_type": None,
    },
    "workflow_name": "PostPerfectPublication",
}

FAKE_TOKEN_269 = json.dumps(
    {
        "status": "vor",
        "expanded_folder": "00269.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "version": "1",
        "force": False,
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
    }
)

FAKE_LAX_MESSAGE_269 = json.dumps(
    {
        "status": "published",
        "requested-action": "publish",
        "datetime": "2013-03-26T00:00:00+00:00",
        "token": base64_encode_string(FAKE_TOKEN_269),
        "id": "269",
        "message": "A message",
    }
)

WORKFLOW_MESSAGE_EXPECTED_269 = {
    "workflow_data": {
        "article_id": "269",
        "expanded_folder": "00269.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "message": "A message",
        "requested_action": "publish",
        "force": False,
        "result": "published",
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "status": "vor",
        "update_date": "2013-03-26T00:00:00Z",
        "version": "1",
        "run_type": None,
    },
    "workflow_name": "PostPerfectPublication",
}

FAKE_SILENT_INGEST_TOKEN = json.dumps(
    {
        "status": "vor",
        "run_type": "silent-correction",
        "expanded_folder": "837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "version": "1",
        "force": True,
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
    }
)

FAKE_SILENT_INGEST_LAX_MESSAGE = json.dumps(
    {
        "datetime": "2013-03-26T00:00:00+00:00",
        "force": True,
        "status": "ingested",
        "id": "837411455",
        "token": base64_encode_string(FAKE_SILENT_INGEST_TOKEN),
        "validate-only": False,
        "requested-action": "ingest",
    }
)

WORKFLOW_MESSAGE_EXPECTED_SILENT_INGEST = {
    "workflow_data": {
        "article_id": "837411455",
        "expanded_folder": "837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "message": None,
        "requested_action": "ingest",
        "force": True,
        "result": "ingested",
        "run": "a8bb05df-2df9-4fce-8f9f-219aca0b0148",
        "status": "vor",
        "update_date": "2013-03-26T00:00:00Z",
        "version": "1",
        "run_type": "silent-correction",
    },
    "workflow_name": "SilentCorrectionsProcess",
}


class TestLaxResponseAdapter(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.laxresponseadapter = LaxResponseAdapter(settings_mock, self.logger)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_listen(self, fake_client):
        directory = TempDirectory()
        fake_queue_messages = [{"Messages": [{"Body": FAKE_LAX_MESSAGE_269}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.lax_response_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
            settings_mock.workflow_starter_queue: FakeSQSQueue(directory),
        }
        fake_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.laxresponseadapter.listen(flag)
        # assertions, should have a message in the out_queue
        out_queue_message = json.loads(bytes_decode(directory.read("fake_sqs_body")))
        self.assertDictEqual(out_queue_message, WORKFLOW_MESSAGE_EXPECTED_269)

    @patch.object(LaxResponseAdapter, "process_message")
    @patch("boto3.client")
    def test_listen_short_retry_exception(self, fake_client, fake_process_message):
        "test when a ShortRetryException exception is raised"
        directory = TempDirectory()
        message_id = "message_id"
        exception_string = "An exception"
        fake_queue_messages = [
            {"Messages": [{"MessageId": message_id, "Body": FAKE_LAX_MESSAGE_269}]}
        ]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.lax_response_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
            settings_mock.workflow_starter_queue: FakeSQSQueue(directory),
        }
        fake_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        # mock the exception
        fake_process_message.side_effect = ShortRetryException(exception_string)
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.laxresponseadapter.listen(flag)
        # assertions
        self.assertEqual(
            self.logger.loginfo[-2],
            "short retry: %s because of %s" % (message_id, exception_string),
        )

    @patch.object(FakeSQSClient, "get_queue_url")
    @patch("boto3.client")
    def test_listen_input_queue_none(self, fake_client, fake_get_queue_url):
        "test if the queue QueueUrl value is None"
        directory = TempDirectory()
        fake_queue_messages = [{"Messages": [{"Body": FAKE_LAX_MESSAGE_269}]}]
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.lax_response_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
            settings_mock.workflow_starter_queue: FakeSQSQueue(directory),
        }
        fake_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        # mock getting the queue url
        fake_get_queue_url.return_value = {}
        # create a fake green flag
        flag = FakeFlag()
        # invoke queue worker to work
        self.laxresponseadapter.listen(flag)
        # assertions
        self.assertEqual(self.logger.logerror, "Could not obtain queue, exiting")

    def test_parse_token_exception(self):
        "exception will be raised trying utils.base64_decode_string on None"
        result = self.laxresponseadapter.parse_token(None)
        self.assertEqual(result.get("run"), None)

    def test_parse_message(self):
        workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_LAX_MESSAGE
        )
        self.assertDictEqual(workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED)

    def test_parse_message_269(self):
        workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_LAX_MESSAGE_269
        )
        self.assertDictEqual(workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED_269)

    def test_parse_message_silent_ingest(self):
        workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_SILENT_INGEST_LAX_MESSAGE
        )
        self.assertDictEqual(
            workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED_SILENT_INGEST
        )

    def test_parse_message_ingest(self):
        "test an ingest message which does not have Force is True in the token"
        fake_message = json.dumps(
            {
                "status": "ingested",
                "requested-action": "ingest",
                "datetime": "2013-03-26T00:00:00+00:00",
                "token": base64_encode_string(json.dumps(test_data.data_ingested_lax)),
                "id": "269",
                "message": "A message",
            }
        )
        expected = {
            "workflow_name": "ProcessArticleZip",
            "workflow_data": {
                "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
                "article_id": "269",
                "version": "1",
                "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
                "status": "vor",
                "result": "ingested",
                "message": "A message",
                "update_date": "2013-03-26T00:00:00Z",
                "requested_action": "ingest",
                "force": False,
                "run_type": None,
            },
        }
        workflow_starter_message = self.laxresponseadapter.parse_message(fake_message)
        self.assertDictEqual(workflow_starter_message, expected)

    @patch.object(LaxResponseAdapter, "parse_token")
    def test_parse_message_exception(self, fake_parse_token):
        fake_parse_token.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.laxresponseadapter.parse_message(FAKE_SILENT_INGEST_LAX_MESSAGE)
        self.assertEqual(
            self.logger.logerror, "Error parsing Lax message. Message: An exception"
        )
