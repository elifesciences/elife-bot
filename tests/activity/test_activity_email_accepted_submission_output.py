import os
import glob
import unittest
from mock import patch
from ddt import ddt, data
import activity.activity_EmailAcceptedSubmissionOutput as activity_module
from activity.activity_EmailAcceptedSubmissionOutput import (
    activity_EmailAcceptedSubmissionOutput as activity_object,
)
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeSession
from tests.activity import settings_mock, test_activity_data


@ddt
class TestEmailAcceptedSubmissionOutput(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @data(
        {
            "comment": "accepted submission zip file example",
            "expected_result": True,
            "expected_email_status": True,
            "expected_email_count": 1,
            "expected_email_subject": (
                "Subject: eLife accepted submission: 30-01-2019-RA-eLife-45644.zip"
            ),
            "expected_email_from": "From: sender@example.org",
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_email_smtp_connect,
        fake_session,
    ):
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # do the activity
        result = self.activity.do_activity(
            test_case_data.ingest_accepted_submission_data
        )
        filename_used = test_case_data.ingest_accepted_submission_data.get("file_name")
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            "failed in {comment}, got {result}, filename {filename}".format(
                comment=test_data.get("comment"),
                result=result,
                filename=filename_used,
            ),
        )
        self.assertEqual(
            self.activity.email_status,
            test_data.get("expected_email_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # check email files and contents
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            # assert 0 or more emails sent
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
        if test_data.get("expected_email_count"):
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0], "r", encoding="utf8") as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(
                        test_data.get("expected_email_subject") in first_email_content
                    )
                if test_data.get("expected_email_from"):
                    self.assertTrue(
                        test_data.get("expected_email_from") in first_email_content
                    )
                if test_data.get("expected_email_body"):
                    self.assertTrue(
                        test_data.get("expected_email_body") in first_email_content
                    )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_send")
    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_do_activity_send_email_false(
        self,
        fake_email_smtp_connect,
        fake_smtp_send,
        fake_session,
    ):
        "test if sending an email returns false"
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_smtp_send.return_value = False
        # do the activity
        result = self.activity.do_activity(
            test_case_data.ingest_accepted_submission_data
        )
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)


class TestEmailSubject(unittest.TestCase):
    def test_accepted_submission_email_subject(self):
        "email subject line with correct output_file value"
        output_file = "file.zip"
        expected = "eLife accepted submission: %s" % output_file
        subject = activity_module.accepted_submission_email_subject(output_file)
        self.assertEqual(subject, expected)