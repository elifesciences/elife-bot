import datetime
import json
import unittest
from mock import patch
from ddt import ddt, data
from testfixtures import TempDirectory
from provider import cleaner, utils
import activity.activity_SilentPublishPreprint as activity_module
from activity.activity_SilentPublishPreprint import (
    activity_SilentPublishPreprint as activity_class,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeSQSClient,
    FakeSQSQueue,
)
from tests.activity import settings_mock, test_activity_data


@ddt
class TestSilentPublishPreprint(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "one article to publish",
            "expected_result": True,
            "expected_published_date_status": True,
            "expected_approved_status": True,
            "expected_queued_status": True,
            "expected_sqs_queue_message": {
                "execution_start_to_close_timeout": "3600",
                "workflow_name": "PostPreprintPublication",
                "workflow_data": {
                    "article_id": 95901,
                    "version": "1",
                    "standalone": False,
                    "run_type": "silent-correction",
                },
            },
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_session,
        fake_sqs_client,
    ):
        directory = TempDirectory()

        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)

        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in [
            "published_date",
            "approved",
            "queued",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value} in {comment}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                    comment=test_data.get("comment"),
                ),
            )
        # check for SQS message
        if test_data.get("expected_sqs_queue_message"):
            out_queue_message = json.loads(
                utils.bytes_decode(directory.read("fake_sqs_body"))
            )
            self.assertDictEqual(
                out_queue_message, test_data.get("expected_sqs_queue_message")
            )

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

    @patch("boto3.client")
    @patch.object(activity_module, "get_session")
    @patch.object(utils, "get_current_datetime")
    @data(
        {
            "comment": "published date is greater than current date",
            "date_time": "2021-01-01 +0000",
            "expected_result": True,
            "expected_published_date_status": True,
            "expected_approved_status": False,
            "expected_queued_status": None,
            "expected_sqs_queue_message": None,
            "expected_activity_log_contains": [
                (
                    "SilentPublishPreprint, published datetime 2024-06-19 14:00:00+00:00"
                    " in the docmap for version DOI 10.7554/eLife.95901.1 is greater than"
                    " the current datetime 2021-01-01 00:00:00+00:00, no silent-correction"
                    " PostPreprintPublication workflow will be started"
                )
            ],
        },
    )
    def test_not_yet_publsihed(
        self,
        test_data,
        fake_get_current_datetime,
        fake_session,
        fake_sqs_client,
    ):
        "test if the published date is in the future, i.e. not yet published"
        directory = TempDirectory()

        # set datetime if specified otherwise use a default datetime
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            test_data.get("date_time", "2025-02-21 +0000"), "%Y-%m-%d %z"
        )

        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)

        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in [
            "published_date",
            "approved",
            "queued",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value} in {comment}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                    comment=test_data.get("comment"),
                ),
            )
        # check for SQS message
        if test_data.get("expected_sqs_queue_message"):
            out_queue_message = json.loads(
                utils.bytes_decode(directory.read("fake_sqs_body"))
            )
            self.assertDictEqual(
                out_queue_message, test_data.get("expected_sqs_queue_message")
            )
        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

    @patch("boto3.client")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "docmap_preprint_history_from_docmap")
    @data(
        {
            "comment": "One XML to generate",
            "expected_result": True,
            "expected_published_date_status": None,
            "expected_approved_status": None,
            "expected_queued_status": None,
            "expected_sqs_queue_message": None,
            "expected_activity_log_contains": [
                (
                    "SilentPublishPreprint, no published date found in the docmap for"
                    " version DOI 10.7554/eLife.95901.1, no silent-correction"
                    " PostPreprintPublication workflow will be started"
                )
            ],
        },
    )
    def test_no_published_date(
        self,
        test_data,
        fake_preprint_history,
        fake_session,
        fake_sqs_client,
    ):
        "test if the docmap has no history_data and therefore no published date"
        directory = TempDirectory()

        fake_preprint_history.return_value = []

        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)

        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in [
            "published_date",
            "approved",
            "queued",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value} in {comment}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                    comment=test_data.get("comment"),
                ),
            )
        # check for SQS message
        if test_data.get("expected_sqs_queue_message"):
            out_queue_message = json.loads(
                utils.bytes_decode(directory.read("fake_sqs_body"))
            )
            self.assertDictEqual(
                out_queue_message, test_data.get("expected_sqs_queue_message")
            )
        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )
