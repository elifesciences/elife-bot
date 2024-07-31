import copy
import os
import glob
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
import activity.activity_EmailMecaOutput as activity_module
from activity.activity_EmailMecaOutput import (
    activity_EmailMecaOutput as activity_class,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeSession
from tests.activity import helpers, settings_mock, test_activity_data


@ddt
class TestEmailMecaOutput(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @data(
        {
            "comment": "MECA file example",
            "expected_result": activity_class.ACTIVITY_SUCCESS,
            "expected_email_status": True,
            "expected_email_count": 1,
            "expected_email_subject": (
                "Subject: eLife ingest MECA: 10.7554/eLife.95901.1"
            ),
            "expected_email_from": "From: sender@example.org",
            "expected_email_body": b"Log messages for version DOI 10.7554/eLife.95901.1",
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_email_smtp_connect,
        fake_session,
    ):
        directory = TempDirectory()
        session = FakeSession(
            copy.copy(test_activity_data.ingest_meca_session_example())
        )
        # add some cleaner_log content
        session.store_value(
            "log_messages",
            b"Log messages",
        )
        fake_session.return_value = session
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
        )
        self.assertEqual(
            self.activity.email_status,
            test_data.get("expected_email_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # check email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
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
                    body = helpers.body_from_multipart_email_string(first_email_content)
                    self.assertTrue(test_data.get("expected_email_body") in body)

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
        directory = TempDirectory()
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_smtp_send.return_value = False
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)


class TestSendEmail(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_send_email_validate_error(
        self,
        fake_email_smtp_connect,
    ):
        "test email subject if email body contains an error"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        version_doi = "10.7554/eLife.95901.1"
        body_content = "ValidateJatsDtd, validation error"
        # do the activity
        result = self.activity.send_email(version_doi, body_content)
        self.assertEqual(result, True)
        # check email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)
        with open(email_files[0], "r", encoding="utf8") as open_file:
            first_email_content = open_file.read()
        self.assertTrue(
            "eLife ingest MECA: Error in 10.7554/eLife.95901.1" in first_email_content
        )


class TestEmailSubject(unittest.TestCase):
    def test_meca_email_subject(self):
        "email subject line with correct output_file value"

        class continuumtest:
            "mock settings object for testing"

        version_doi = "10.7554/eLife.95901.1"
        expected = "TEST eLife ingest MECA: %s" % version_doi
        subject = activity_module.meca_email_subject(version_doi, continuumtest)
        self.assertEqual(subject, expected)

    def test_meca_email_subject_error(self):
        "email subject for an error email"
        version_doi = "10.7554/eLife.95901.1"
        error = True
        expected = "eLife ingest MECA: Error in %s" % version_doi
        subject = activity_module.meca_email_subject(version_doi, settings_mock, error)
        self.assertEqual(subject, expected)

    def test_no_settings_class_name(self):
        "test if the settings is not a class"
        version_doi = "10.7554/eLife.95901.1"
        expected = "eLife ingest MECA: %s" % version_doi
        subject = activity_module.meca_email_subject(version_doi, settings_mock)
        self.assertEqual(subject, expected)

    def test_settings_none(self):
        "test if settings is not passed as an argument"
        version_doi = "10.7554/eLife.95901.1"
        expected = "eLife ingest MECA: %s" % version_doi
        subject = activity_module.meca_email_subject(version_doi)
        self.assertEqual(subject, expected)
