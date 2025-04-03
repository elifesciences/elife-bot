# coding=utf-8

import unittest
import os
import copy
from mock import patch
from testfixtures import TempDirectory
import activity.activity_ConfirmPreprintPDF as activity_module
from activity.activity_ConfirmPreprintPDF import (
    activity_ConfirmPreprintPDF as activity_class,
)
from tests import list_files
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeSQSClient,
    FakeSQSQueue,
    FakeStorageContext,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestConfirmPreprintPdf(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("boto3.client")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_sqs_client,
    ):
        "test if there is a pdf_url in the session"
        directory = TempDirectory()

        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        session_dict = copy.copy(SESSION_DICT)
        session_dict["pdf_url"] = pdf_url
        fake_session.return_value = FakeSession(session_dict)

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertTrue(
            "ConfirmPreprintPDF, for article_id %s version %s found pdf_url %s"
            % (session_dict.get("article_id"), session_dict.get("version"), pdf_url)
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ConfirmPreprintPDF, starting a FinishPreprintPublication workflow"
                " for article_id %s, version %s"
            )
            % (session_dict.get("article_id"), session_dict.get("version"))
            in self.activity.logger.loginfo,
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_no_pdf_url(
        self,
        fake_session,
        fake_storage_context,
    ):
        "test if no pdf_url is in the session"
        directory = TempDirectory()

        session_dict = copy.copy(SESSION_DICT)
        fake_session.return_value = FakeSession(session_dict)
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        self.assertTrue(
            "ConfirmPreprintPDF, for article_id %s version %s found pdf_url %s"
            % (session_dict.get("article_id"), session_dict.get("version"), None)
            in self.activity.logger.loginfo,
        )

        outbox_path = os.path.join(directory.path, "finish_preprint/outbox")
        self.assertTrue(os.path.exists(outbox_path))
        outbox_files = list_files(outbox_path)
        self.assertEqual(outbox_files, ["elife-preprint-95901-v1.xml"])
