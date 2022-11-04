import unittest
import json
from mock import patch
import botocore
from tests import settings_mock
from tests.classes_mock import FakeFlag, FakeSWFClient
from tests.activity.classes_mock import FakeLogger
import worker
from activity.activity_PingWorker import activity_PingWorker as activity_class


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.activity_json = None
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
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
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
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


class TestProcessActivity(unittest.TestCase):
    def setUp(self):
        self.flag = FakeFlag(0.001)
        self.logger = FakeLogger()
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
            self.activity_json = json.loads(open_file.read())
        # change the activity name to PingWorker and mock its return value
        self.activity_json["activityType"]["name"] = "PingWorker"
        self.token = "token"

    def test_process_activity(self):
        "typical situation"
        # invoke process_activity
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_completed returned None" in str(self.logger.loginfo)
        )

    @patch.object(activity_class, "do_activity")
    def test_process_activity_respond_activity_success(self, fake_do_activity):
        "change the activity eturn value ACTIVITY_SUCCESS"
        fake_do_activity.return_value = activity_class.ACTIVITY_SUCCESS
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_completed returned None" in str(self.logger.loginfo)
        )

    @patch.object(activity_class, "do_activity")
    def test_process_activity_respond_activity_temporary_failure(
        self, fake_do_activity
    ):
        "change the activity eturn value ACTIVITY_TEMPORARY_FAILURE"
        fake_do_activity.return_value = activity_class.ACTIVITY_TEMPORARY_FAILURE
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertTrue(
            "respond_activity_task_failed returned None" in str(self.logger.loginfo)
        )

    @patch.object(activity_class, "do_activity")
    def test_process_activity_respond_activity_permanent_failure(
        self, fake_do_activity
    ):
        "change the activity eturn value ACTIVITY_PERMANENT_FAILURE"
        fake_do_activity.return_value = activity_class.ACTIVITY_PERMANENT_FAILURE
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertTrue(
            "request_cancel_workflow_execution None" in str(self.logger.loginfo)
        )

    @patch.object(activity_class, "do_activity")
    def test_process_activity_respond_activity_exit_workflow(self, fake_do_activity):
        "change the activity eturn value ACTIVITY_EXIT_WORKFLOW"
        fake_do_activity.return_value = activity_class.ACTIVITY_EXIT_WORKFLOW
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertTrue(
            "request_cancel_workflow_execution None" in str(self.logger.loginfo)
        )

    @patch.object(activity_class, "do_activity")
    def test_process_activity_exception(self, fake_do_activity):
        "test an exception raised by the activity"
        fake_do_activity.side_effect = Exception("An exception")
        worker.process_activity(
            self.activity_json, settings_mock, self.logger, FakeSWFClient(), self.token
        )
        # make some assertions on log values
        self.assertEqual(self.logger.logerror, "error executing activity %s")


class TestRespondCompleted(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.token = "token"
        self.message = "message"

    def test_respond_completed(self):
        client = FakeSWFClient()
        worker.respond_completed(
            client,
            self.logger,
            self.token,
            self.message,
        )
        self.assertEqual(
            self.logger.loginfo[-1], "respond_activity_task_completed returned None"
        )

    @patch.object(FakeSWFClient, "respond_activity_task_completed")
    def test_respond_completed_exception(self, fake_request):
        client = FakeSWFClient()
        exception_error_code = "UnknownResourceFault"
        exception_operation_name = "operation_name"
        fake_request.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": exception_error_code}},
            exception_operation_name,
        )
        worker.respond_completed(
            client,
            self.logger,
            self.token,
            self.message,
        )
        self.assertEqual(
            self.logger.logexception,
            "SWF client exception: An error occurred (%s) when calling the %s operation: Unknown"
            % (exception_error_code, exception_operation_name),
        )


class TestRespondFailed(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.token = "token"
        self.details = "details"
        self.reason = "reason"

    def test_respond_failed(self):
        client = FakeSWFClient()
        worker.respond_failed(
            client,
            self.logger,
            self.token,
            self.details,
            self.reason,
        )
        self.assertEqual(
            self.logger.loginfo[-1], "respond_activity_task_failed returned None"
        )

    @patch.object(FakeSWFClient, "respond_activity_task_failed")
    def test_respond_failed_exception(self, fake_request):
        client = FakeSWFClient()
        exception_error_code = "UnknownResourceFault"
        exception_operation_name = "operation_name"
        fake_request.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": exception_error_code}},
            exception_operation_name,
        )
        worker.respond_failed(
            client,
            self.logger,
            self.token,
            self.details,
            self.reason,
        )
        self.assertEqual(
            self.logger.logexception,
            "SWF client exception: An error occurred (%s) when calling the %s operation: Unknown"
            % (exception_error_code, exception_operation_name),
        )


class TestSignalFailWorkflow(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.domain = "domain"
        self.workflow_id = "workflow_id"
        self.run_id = "run_id"

    def test_signal_fail_workflow(self):
        client = FakeSWFClient()
        worker.signal_fail_workflow(
            client,
            self.logger,
            self.domain,
            self.workflow_id,
            self.run_id,
        )
        self.assertEqual(
            self.logger.loginfo[-1], "request_cancel_workflow_execution None"
        )

    @patch.object(FakeSWFClient, "request_cancel_workflow_execution")
    def test_signal_fail_workflow_exception(self, fake_request):
        client = FakeSWFClient()
        exception_error_code = "UnknownResourceFault"
        exception_operation_name = "operation_name"
        fake_request.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": exception_error_code}},
            exception_operation_name,
        )
        worker.signal_fail_workflow(
            client,
            self.logger,
            self.domain,
            self.workflow_id,
            self.run_id,
        )
        self.assertEqual(
            self.logger.logexception,
            "SWF client exception: An error occurred (%s) when calling the %s operation: Unknown"
            % (exception_error_code, exception_operation_name),
        )
