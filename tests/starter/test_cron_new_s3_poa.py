import unittest
import json
from mock import patch
import botocore
from testfixtures import TempDirectory
from S3utility.s3_sqs_message import S3SQSMessage
import starter.cron_NewS3POA as starter_module
from starter.cron_NewS3POA import cron_NewS3POA
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger, FakeSQSClient, FakeSQSQueue
from tests import settings_mock, test_data


class TestCronNewS3POA(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = cron_NewS3POA(settings_mock, logger=self.fake_logger)
        # queue data for reuse
        # create an S3 event message
        self.records = test_data.test_s3_event_records(
            bucket="poa", key="18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
        )
        self.fake_queue_messages = [
            {"Messages": [{"ReceiptHandle": "id", "Body": json.dumps(self.records)}]}
        ]

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("starter.cron_NewS3POA.sqs_connect")
    @patch("starter.objects.boto3.client")
    def test_start(self, fake_swf_client, fake_sqs_client):
        directory = TempDirectory()
        fake_swf_client.return_value = FakeSWFClient()
        # mock the SQS client and queues
        fake_queues = {
            settings_mock.poa_incoming_queue: FakeSQSQueue(
                directory, self.fake_queue_messages
            ),
        }
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        self.assertIsNone(self.starter.start(settings_mock))

    @patch("tests.activity.classes_mock.FakeSQSClient.receive_message")
    @patch("starter.cron_NewS3POA.sqs_connect")
    @patch("starter.objects.boto3.client")
    def test_start_no_messages(
        self, fake_swf_client, fake_sqs_client, fake_receive_message
    ):
        directory = TempDirectory()
        fake_swf_client.return_value = FakeSWFClient()
        fake_sqs_client.return_value = FakeSQSClient(directory)
        fake_receive_message.return_value = {}
        # mock_queue.return_value = FakeSQSQueue(directory)
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeSWFClient, "start_workflow_execution")
    @patch("starter.cron_NewS3POA.sqs_connect")
    @patch("starter.objects.boto3.client")
    def test_start_exception_old(self, fake_swf_client, fake_sqs_client, fake_start):
        directory = TempDirectory()
        fake_swf_client.return_value = FakeSWFClient()
        fake_queues = {
            settings_mock.poa_incoming_queue: FakeSQSQueue(
                directory, self.fake_queue_messages
            ),
        }
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        mock_exception = botocore.exceptions.ClientError(
            {"Error": {"Code": "WorkflowExecutionAlreadyStartedFault"}},
            "operation_name",
        )
        fake_start.side_effect = mock_exception
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeSQSClient, "receive_message")
    def test_get_queue_messages_exception(self, fake_receive_message):
        directory = TempDirectory()
        fake_sqs_client = FakeSQSClient(directory)
        fake_receive_message.side_effect = Exception("Get messages exception")
        with self.assertRaises(Exception):
            starter_module.get_queue_messages(
                fake_sqs_client, "queue_url", 1, FakeLogger()
            )

    @patch.object(FakeSQSClient, "receive_message")
    def test_process_queue_exception(self, fake_receive_message):
        directory = TempDirectory()
        fake_sqs_client = FakeSQSClient(directory)
        fake_receive_message.side_effect = Exception("Get messages exception")
        logger = FakeLogger()
        starter_module.process_queue(fake_sqs_client, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            "Breaking process queue read loop, failed to get messages from queue",
        )

    def test_process_queue_ignored_message(self):
        directory = TempDirectory()
        logger = FakeLogger()
        # change the message Body so it is not considered an S3Event
        records = {"foo": "bar"}
        fake_queue_messages = [
            {"Messages": [{"ReceiptHandle": "id", "Body": json.dumps(records)}]}
        ]
        fake_queues = {
            settings_mock.poa_incoming_queue: FakeSQSQueue(
                directory, fake_queue_messages
            ),
        }
        fake_sqs_client = FakeSQSClient(directory, queues=fake_queues)
        starter_module.process_queue(fake_sqs_client, settings_mock, logger)
        self.assertEqual(
            logger.loginfo[-2],
            "Message not processed, deleting it from queue: %s" % records,
        )
        self.assertEqual(logger.loginfo[-1], "no messages available")

    @patch.object(starter_module, "start_package_poa_workflow")
    def test_process_queue_starter_exception(self, fake_start_workflow):
        directory = TempDirectory()

        logger = FakeLogger()
        fake_queues = {
            settings_mock.poa_incoming_queue: FakeSQSQueue(
                directory, self.fake_queue_messages
            ),
        }
        fake_sqs_client = FakeSQSClient(directory, queues=fake_queues)
        fake_start_workflow.side_effect = Exception("Failed to start workflow")
        starter_module.process_queue(fake_sqs_client, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            "Exception processing message, deleting it from queue: %s" % self.records,
        )

    @patch("starter.objects.boto3.client")
    def test_start_package_poa_workflow_exception(self, fake_swf_client):
        s3_message = S3SQSMessage(body=json.dumps(self.records))
        logger = FakeLogger()
        fake_swf_client.side_effect = Exception("Failed to start workflow")
        with self.assertRaises(Exception):
            starter_module.start_package_poa_workflow(s3_message, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            (
                "Error: starting starter_PackagePOA for document "
                "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
            ),
        )
