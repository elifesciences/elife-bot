# coding=utf-8

import os
import glob
import unittest
from mock import patch
from ddt import ddt, data
import activity.activity_DecisionLetterReceipt as activity_module
from activity.activity_DecisionLetterReceipt import (
    activity_DecisionLetterReceipt as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer


def input_data(file_name_to_change=''):
    activity_data = test_case_data.ingest_decision_letter_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestDecisionLetterReceipt(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, self.fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @data(
        {
            "comment": 'decision letter zip file example',
            "filename": 'elife-39122.zip',
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_email_count": 2,
            "expected_email_subject": (
                "Subject: Decision letter workflow completed! file: elife-39122.zip"),
            "expected_email_from": "From: sender@example.org"
        },
    )
    def test_do_activity(self, test_data, fake_email_smtp_connect):
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        # check result
        self.assertEqual(
            result, test_data.get("expected_result"),
            ('failed in {comment}, got {result}, filename {filename}').format(
                comment=test_data.get("comment"),
                result=result,
                filename=filename_used))
        # check assertions on email files and contents
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0]) as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(test_data.get("expected_email_subject") in first_email_content)
                if test_data.get("expected_email_from"):
                    self.assertTrue(test_data.get("expected_email_from") in first_email_content)

    @patch.object(activity_module.email_provider, 'simple_email_body')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    def test_do_activity_exception(self, fake_email_smtp_connect, fake_email_body):
        filename = 'elife-39122.zip'
        expected_result = activity_object.ACTIVITY_TEMPORARY_FAILURE
        expected_email_count = 0
        expected_exception_log_message = (
            'Exception raised sending email in DecisionLetterReceipt for file elife-39122.zip.')
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_email_body.side_effect = Exception('Some exception')
        # do the activity
        result = self.activity.do_activity(input_data(filename))
        # check result
        self.assertEqual(result, expected_result)
        # check assertions on emails
        email_files_filter = os.path.join(self.activity.get_tmp_dir(), "*.eml")
        email_files = glob.glob(email_files_filter)
        self.assertEqual(len(email_files), expected_email_count)
        self.assertEqual(self.fake_logger.logexception, expected_exception_log_message)
