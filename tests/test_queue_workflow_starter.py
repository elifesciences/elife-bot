import unittest
import json
from mock import patch
from testfixtures import TempDirectory
from tests import settings_mock
from tests.classes_mock import FakeFlag, FakeSWFClient
from tests.activity.classes_mock import FakeSQSMessage, FakeSQSQueue, FakeLogger
import queue_workflow_starter


class TestQueueWorkflowStarter(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("tests.activity.classes_mock.FakeSQSQueue.get_messages")
    @patch("queue_workflow_starter.get_queue")
    @patch("boto3.client")
    @patch("log.logger")
    def test_main(self, fake_logger, fake_client, mock_queue, mock_queue_read):
        directory = TempDirectory()
        message_body = json.dumps({"workflow_name": "Ping", "workflow_data": {}})
        fake_client.return_value = FakeSWFClient()
        mock_logger = FakeLogger()
        fake_logger.return_value = mock_logger
        mock_queue.return_value = FakeSQSQueue(directory)
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        mock_queue_read.return_value = [fake_message]
        queue_workflow_starter.main(settings_mock, FakeFlag())
        self.assertTrue("Starting workflow: Ping_" in str(mock_logger.loginfo))

    @patch("boto3.client")
    @patch("log.logger")
    def test_process_message(self, fake_logger, fake_client):
        directory = TempDirectory()
        message_body = json.dumps(
            {"workflow_name": "PubmedArticleDeposit", "workflow_data": {}}
        )
        fake_client.return_value = FakeSWFClient()
        mock_logger = FakeLogger()
        fake_logger.return_value = mock_logger
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(
            settings_mock, FakeLogger(), fake_message
        )
        self.assertTrue(
            "Starting workflow: PubmedArticleDeposit" in str(mock_logger.loginfo)
        )

    @patch("boto3.client")
    @patch("log.logger")
    def test_process_message_no_data_processor(self, fake_logger, fake_client):
        directory = TempDirectory()
        message_body = json.dumps({"workflow_name": "Ping", "workflow_data": {}})
        fake_client.return_value = FakeSWFClient()
        mock_logger = FakeLogger()
        fake_logger.return_value = mock_logger
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(
            settings_mock, FakeLogger(), fake_message
        )
        self.assertTrue("Starting workflow: Ping_" in str(mock_logger.loginfo))

    @patch("boto3.client")
    @patch("log.logger")
    def test_process_message_fail_to_start_workflow(self, fake_logger, fake_client):
        directory = TempDirectory()
        message_body = json.dumps(
            {"workflow_name": "not_a_real_workflow", "workflow_data": {}}
        )
        fake_client.return_value = FakeSWFClient()
        mock_logger = FakeLogger()
        fake_logger.return_value = mock_logger
        fake_message = FakeSQSMessage(directory)
        fake_message.set_body(message_body)
        queue_workflow_starter.process_message(
            settings_mock, FakeLogger(), fake_message
        )
        # log only contains the First logger info message since no workflow was started
        self.assertTrue(len(mock_logger.loginfo) == 1)

    def test_process_data_ingestarticlezip(self):
        workflow_data = {
            "event_name": "",
            "event_time": "",
            "bucket_name": "",
            "file_name": "",
            "file_etag": "",
            "file_size": "",
        }
        data = queue_workflow_starter.process_data_ingestarticlezip(workflow_data)
        s3_notification_dict = data.get("info").to_dict()
        self.assertEqual(sorted(s3_notification_dict), sorted(workflow_data))
        self.assertIsNotNone(data.get("run"))

    def test_process_data_postperfectpublication(self):
        workflow_data = {"some": "data"}
        data = queue_workflow_starter.process_data_postperfectpublication(workflow_data)
        self.assertEqual(sorted(data.get("info")), sorted(workflow_data))

    def test_process_data_ingestdigest(self):
        workflow_data = {
            "event_name": "",
            "event_time": "",
            "bucket_name": "",
            "file_name": "",
            "file_etag": "",
            "file_size": "",
        }
        data = queue_workflow_starter.process_data_ingestdigest(workflow_data)
        s3_notification_dict = data.get("info").to_dict()
        self.assertEqual(sorted(s3_notification_dict), sorted(workflow_data))
        self.assertIsNotNone(data.get("run"))

    def test_process_data_ingestdecisionletter(self):
        workflow_data = {
            "event_name": "",
            "event_time": "",
            "bucket_name": "",
            "file_name": "",
            "file_etag": "",
            "file_size": "",
        }
        data = queue_workflow_starter.process_data_ingestdecisionletter(workflow_data)
        s3_notification_dict = data.get("info").to_dict()
        self.assertEqual(sorted(s3_notification_dict), sorted(workflow_data))
        self.assertIsNotNone(data.get("run"))


if __name__ == "__main__":
    unittest.main()
