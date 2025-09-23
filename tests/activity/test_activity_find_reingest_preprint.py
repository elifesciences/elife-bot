# coding=utf-8

import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider
from activity.activity_FindReingestPreprint import (
    activity_FindReingestPreprint as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeSQSClient,
    FakeSQSQueue,
)


class TestFindReingestPreprint(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("boto3.client")
    @patch.object(github_provider, "find_github_issues_by_assignee")
    def test_do_activity(
        self,
        fake_find_github_issues,
        fake_sqs_client,
    ):
        directory = TempDirectory()

        issue_1 = FakeGithubIssue(
            title="MSID: 96848 Version: 2 DOI: 10.1101/2024.01.31.xxxx96848",
            number=1,
        )
        issue_2 = FakeGithubIssue(
            title="MSID: 95901 Version: 1 DOI: 10.1101/2024.01.31.xxxx95901",
            number=2,
        )
        issue_3 = FakeGithubIssue(
            title="MSID: 666 Version: None",
            number=2,
        )
        issue_4 = FakeGithubIssue(
            title="MSID: None Version: 1",
            number=2,
        )
        issue_1.assignees = [settings_mock.github_named_user]
        issue_2.assignees = [settings_mock.github_named_user]
        issue_3.assignees = [settings_mock.github_named_user]
        issue_4.assignees = [settings_mock.github_named_user]
        fake_find_github_issues.return_value = [issue_1, issue_2, issue_3, issue_4]

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        expected_result = activity_class.ACTIVITY_SUCCESS

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertTrue(
            "FindReingestPreprint, starting a IngestMeca workflow for article_id 96848, version 2"
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            "FindReingestPreprint, removing assignee github_user_name from the Github issue"
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "FindReingestPreprint, could not parse the article_id and version"
                " from the Github issue title 'MSID: 666 Version: None'"
            )
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "FindReingestPreprint, could not parse the article_id and version"
                " from the Github issue title 'MSID: None Version: 1'"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(github_provider, "find_github_issues_by_assignee")
    def test_do_activity_find_github_exception(
        self,
        fake_find_github_issues,
    ):
        "test if finding Github issues raises an exception"
        exception_message = "An exception"
        fake_find_github_issues.side_effect = Exception(exception_message)
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "FindReingestPreprint, exception getting issues from github by assignee %s: %s"
            % (settings_mock.github_named_user, exception_message),
        )

    @patch.object(github_provider, "find_github_issues_by_assignee")
    def test_do_activity_no_issues(
        self,
        fake_find_github_issues,
    ):
        "test if no issues are found in Github assigned to the named user"
        fake_find_github_issues.return_value = []
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "FindReingestPreprint, no Github issues assigned to %s"
            % settings_mock.github_named_user,
        )

    @patch.object(github_provider, "remove_github_issue_assignee")
    @patch("boto3.client")
    @patch.object(github_provider, "find_github_issues_by_assignee")
    def test_do_activity_issue_processing_exception(
        self,
        fake_find_github_issues,
        fake_sqs_client,
        fake_remove_assignee,
    ):
        "test processing an issue raises an exception"
        directory = TempDirectory()

        issue_title = "MSID: 96848 Version: 2 DOI: 10.1101/2024.01.31.xxxx96848"
        issue = FakeGithubIssue(
            title=issue_title,
            number=1,
        )
        issue.assignees = [settings_mock.github_named_user]
        fake_find_github_issues.return_value = [issue]

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        exception_message = "An exception"
        fake_remove_assignee.side_effect = Exception(exception_message)

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "FindReingestPreprint, exception raised processing issue '%s': %s"
            % (issue_title, exception_message),
        )


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.github_named_user = settings_mock.github_named_user

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.github_named_user = self.github_named_user

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.github_named_user
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "FindReingestPreprint, "
                "github_named_user in settings is missing, skipping"
            ),
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.github_named_user = settings_mock.github_named_user

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.github_named_user = self.github_named_user

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.github_named_user = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "FindReingestPreprint, "
                "github_named_user in settings is blank, skipping"
            ),
        )
