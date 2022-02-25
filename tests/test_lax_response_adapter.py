import unittest
import json
from mock import patch
from testfixtures import TempDirectory
from lax_response_adapter import LaxResponseAdapter
from provider.utils import base64_encode_string, bytes_decode
from tests import settings_mock
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
    }
)

WORKFLOW_MESSAGE_EXPECTED_269 = {
    "workflow_data": {
        "article_id": "269",
        "expanded_folder": "00269.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148",
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

    def test_parse_message(self):
        expected_workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_LAX_MESSAGE
        )
        self.assertDictEqual(
            expected_workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED
        )

    def test_parse_message_269(self):
        expected_workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_LAX_MESSAGE_269
        )
        self.assertDictEqual(
            expected_workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED_269
        )

    def test_parse_message_silent_ingest(self):
        expected_workflow_starter_message = self.laxresponseadapter.parse_message(
            FAKE_SILENT_INGEST_LAX_MESSAGE
        )
        self.assertDictEqual(
            expected_workflow_starter_message, WORKFLOW_MESSAGE_EXPECTED_SILENT_INGEST
        )


if __name__ == "__main__":
    unittest.main()
