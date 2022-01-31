import unittest
import json
from mock import patch
from tests import settings_mock
from tests.classes_mock import FakeFlag, FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import worker
from activity.activity_PingWorker import activity_PingWorker as activity_class


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.activity_json = None
        with open("tests/test_data/activity.json", "r") as open_file:
            self.activity_json = json.loads(open_file.read())

    def test_get_task_token(self):
        expected = (
            "AAAAKgAAAAEAAAAAAAAAAiTLU1nb+mIAOocBiGYTsSABMWaY3FM6Ib1SU1w+SRp1WIYxSmbtunYFMcfJs0"
            + "LqS4bYWhNsYZIkrH7XGRwkgqx8IDM9o6m8BT9sQVUM6NRNxsbZlFUxFh1p6vpXVHWt64hB/9WvlrF8qWNR"
            + "+gx9HTkCHJyfEdsk+3PFCjApQ6+YBtdZLmRw3iHLVT45LvuFnwdBCP+bk5ACOcYi8hcm89qVKMBjtLjZTD"
            + "N0BAVyFX1/V+7zFnaEzrqErdcirHBA7/PHdcsYJpA1V37drsAL50N9U6MVMaYWmFlP7IPJPY4M"
        )
        task_token = worker.get_taskToken(self.activity_json)
        self.assertEqual(task_token, expected)

    def test_get_task_token_failure(self):
        task_token = worker.get_taskToken({})
        self.assertIsNone(task_token)

    def test_get_activity_type(self):
        expected = "Sum"
        activity_type = worker.get_activityType(self.activity_json)
        self.assertEqual(activity_type, expected)

    def test_get_activity_type_failure(self):
        activity_type = worker.get_activityType({})
        self.assertIsNone(activity_type)

    def test_get_input(self):
        expected = {"data": [1, 3, 7, 11]}
        worker_input = worker.get_input(self.activity_json)
        self.assertEqual(worker_input, expected)

    def test_get_input_failure(self):
        worker_input = worker.get_input({})
        self.assertIsNone(worker_input)

    def test_get_activity_name(self):
        activity_type = "PingWorker"
        expected = "activity_PingWorker"
        activity_name = worker.get_activity_name(activity_type)
        self.assertEqual(activity_name, expected)

    def test_import_activity_class(self):
        activity_name = "activity_PingWorker"
        result = worker.import_activity_class(activity_name)
        self.assertTrue(result)

    def test_import_activity_class_failure(self):
        activity_name = "this_activity_does_not_exist"
        result = worker.import_activity_class(activity_name)
        self.assertFalse(result)

    def test_get_activity_object(self):
        activity_name = "activity_PingWorker"
        worker.import_activity_class(activity_name)
        activity_object = worker.get_activity_object(
            activity_name, settings_mock, None, None, None, None
        )
        self.assertEqual(activity_object.__class__.__name__, activity_name)


class TestWorkerWork(unittest.TestCase):
    def setUp(self):
        self.flag = FakeFlag(0.001)
        self.logger = FakeLogger()
        with open("tests/test_data/activity.json", "r") as open_file:
            self.activity_json = json.loads(open_file.read())

    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_respond_failed(self, fake_client, fake_poll, fake_get_logger):
        "test will not be able to find activity_Sum, which no longer exists"
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        fake_poll.return_value = self.activity_json
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "error: could not load object activity_Sum" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_completed(self, fake_client, fake_poll, fake_get_logger):
        "change the activity name to PingWorker which does exist"
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_completed returned None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch.object(activity_class, "do_activity")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_failed(
        self, fake_client, fake_poll, fake_get_logger, fake_do_activity
    ):
        "change the activity name to PingWorker and mock its return value"
        activity_return_value = False
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        fake_do_activity.return_value = activity_return_value
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_failed returned None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch.object(activity_class, "do_activity")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_activity_success(
        self, fake_client, fake_poll, fake_get_logger, fake_do_activity
    ):
        "change the activity name to PingWorker and new style return value ACTIVITY_SUCCESS"
        activity_return_value = activity_class.ACTIVITY_SUCCESS
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        fake_do_activity.return_value = activity_return_value
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_completed returned None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch.object(activity_class, "do_activity")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_activity_temporary_failure(
        self, fake_client, fake_poll, fake_get_logger, fake_do_activity
    ):
        "change the activity name to PingWorker and new style return value ACTIVITY_TEMPORARY_FAILURE"
        activity_return_value = activity_class.ACTIVITY_TEMPORARY_FAILURE
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        fake_do_activity.return_value = activity_return_value
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_failed returned None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch.object(activity_class, "do_activity")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_activity_permanent_failure(
        self, fake_client, fake_poll, fake_get_logger, fake_do_activity
    ):
        "change the activity name to PingWorker and new style return value ACTIVITY_PERMANENT_FAILURE"
        activity_return_value = activity_class.ACTIVITY_PERMANENT_FAILURE
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        fake_do_activity.return_value = activity_return_value
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "request_cancel_workflow_execution None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")

    @patch.object(activity_class, "do_activity")
    @patch("logging.getLogger")
    @patch.object(FakeSWFClient, "poll_for_activity_task")
    @patch("boto3.client")
    def test_work_ping_respond_activity_exit_workflow(
        self, fake_client, fake_poll, fake_get_logger, fake_do_activity
    ):
        "change the activity name to PingWorker and new style return value ACTIVITY_EXIT_WORKFLOW"
        activity_return_value = activity_class.ACTIVITY_EXIT_WORKFLOW
        fake_get_logger.return_value = self.logger
        fake_client.return_value = FakeSWFClient()
        self.activity_json["activityType"]["name"] = "PingWorker"
        fake_poll.return_value = self.activity_json
        fake_do_activity.return_value = activity_return_value
        # invoke work
        worker.work(settings_mock, self.flag)
        # make some assertions on log values
        self.assertTrue(
            "request_cancel_workflow_execution None" in str(self.logger.loginfo)
        )
        self.assertEqual(self.logger.loginfo[-1], "graceful shutdown")


if __name__ == "__main__":
    unittest.main()
