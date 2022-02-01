import unittest
from mock import patch
import botocore
from testfixtures import TempDirectory
import starter.cron_NewS3POA as starter_module
from starter.cron_NewS3POA import cron_NewS3POA
from tests.classes_mock import FakeSWFClient, FakeS3Event
from tests.activity.classes_mock import FakeLogger, FakeSQSConn, FakeSQSQueue
import tests.settings_mock as settings_mock


class TestCronNewS3POA(unittest.TestCase):
    def setUp(self):
        self.fake_logger = FakeLogger()
        self.starter = cron_NewS3POA(settings_mock, logger=self.fake_logger)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(starter_module, "get_sqs_queue")
    @patch.object(starter_module, "sqs_connect")
    @patch("boto3.client")
    def test_start(self, fake_client, mock_sqs_connect, mock_queue):
        directory = TempDirectory()
        fake_client.return_value = FakeSWFClient()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        s3_event = FakeS3Event()
        mock_queue.return_value = FakeSQSQueue(directory, messages=[s3_event])
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(starter_module, "get_sqs_queue")
    @patch.object(starter_module, "sqs_connect")
    @patch("boto3.client")
    def test_start_no_messages(self, fake_client, mock_sqs_connect, mock_queue):
        directory = TempDirectory()
        fake_client.return_value = FakeSWFClient()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeSWFClient, "start_workflow_execution")
    @patch.object(starter_module, "get_sqs_queue")
    @patch.object(starter_module, "sqs_connect")
    @patch("boto3.client")
    def test_start_exception(
        self, fake_client, mock_sqs_connect, mock_queue, fake_start
    ):
        directory = TempDirectory()
        fake_client.return_value = FakeSWFClient()
        mock_sqs_connect.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        mock_exception = botocore.exceptions.ClientError(
            {"Error": {"Code": "WorkflowExecutionAlreadyStartedFault"}},
            "operation_name",
        )
        fake_start.side_effect = mock_exception
        self.assertIsNone(self.starter.start(settings_mock))

    @patch.object(FakeSQSQueue, "get_messages")
    def test_get_queue_messages_exception(self, fake_get_messages):
        directory = TempDirectory()
        fake_queue = FakeSQSQueue(directory)
        fake_get_messages.side_effect = Exception("Get messages exception")
        with self.assertRaises(Exception):
            starter_module.get_queue_messages(fake_queue, 1, FakeLogger())

    @patch.object(FakeSQSQueue, "get_messages")
    def test_process_queue_exception(self, fake_get_messages):
        directory = TempDirectory()
        fake_queue = FakeSQSQueue(directory)
        fake_get_messages.side_effect = Exception("Get messages exception")
        logger = FakeLogger()
        starter_module.process_queue(fake_queue, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            "Breaking process queue read loop, failed to get messages from queue",
        )

    def test_process_queue_ignored_message(self):
        directory = TempDirectory()
        s3_event = FakeS3Event()
        logger = FakeLogger()
        # here change the event type so it is ignored
        s3_event.notification_type = "foo"
        fake_queue = FakeSQSQueue(directory, messages=[s3_event])
        starter_module.process_queue(fake_queue, settings_mock, logger)
        self.assertEqual(
            logger.loginfo[-2], "Message not processed, deleting it from queue: "
        )
        self.assertEqual(logger.loginfo[-1], "no messages available")

    @patch.object(starter_module, "start_package_poa_workflow")
    def test_process_queue_starter_exception(self, fake_start_workflow):
        directory = TempDirectory()
        s3_event = FakeS3Event()
        logger = FakeLogger()
        fake_queue = FakeSQSQueue(directory, messages=[s3_event])
        fake_start_workflow.side_effect = Exception("Failed to start workflow")
        starter_module.process_queue(fake_queue, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            "Exception processing message, deleting it from queue: ",
        )

    @patch("boto3.client")
    def test_start_package_poa_workflow_exception(self, fake_client):
        s3_event = FakeS3Event()
        logger = FakeLogger()
        fake_client.side_effect = Exception("Failed to start workflow")
        with self.assertRaises(Exception):
            starter_module.start_package_poa_workflow(s3_event, settings_mock, logger)
        self.assertEqual(
            logger.logexception,
            "Error: starting starter_PackagePOA for document elife-00353-vor-r1.zip",
        )
