# coding=utf-8

import unittest
from mock import patch
from provider import github_provider
import activity.activity_AddPreprintIssueLabel as activity_module
from activity.activity_AddPreprintIssueLabel import (
    activity_AddPreprintIssueLabel as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestAddPreprintIssueLabel(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    @patch.object(activity_module, "get_session")
    @patch.object(github_provider, "find_github_issue")
    def test_do_activity(
        self,
        fake_find_github_issue,
        fake_session,
    ):
        github_issue = FakeGithubIssue()
        fake_find_github_issue.return_value = github_issue
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertTrue(
            (
                "AddPreprintIssueLabel, added label to Github issue found for"
                " version DOI 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(activity_module, "get_session")
    @patch.object(github_provider, "find_github_issue")
    def test_do_activity_no_issue_found(
        self,
        fake_find_github_issue,
        fake_session,
    ):
        "test when no Github issue is found"
        fake_find_github_issue.return_value = None
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertTrue(
            (
                "AddPreprintIssueLabel, no open Github issue found for"
                " version DOI 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(activity_module, "get_session")
    @patch.object(github_provider, "find_github_issue")
    def test_do_activity_find_issue_exception(
        self,
        fake_find_github_issue,
        fake_session,
    ):
        "test exception raised finding Github issue"
        fake_find_github_issue.side_effect = Exception("An exception")
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(github_provider, "add_label_to_github_issue")
    @patch.object(activity_module, "get_session")
    @patch.object(github_provider, "find_github_issue")
    def test_do_activity_add_label_exception(
        self,
        fake_find_github_issue,
        fake_session,
        fake_add_label,
    ):
        "test exception raised adding a label"
        github_issue = FakeGithubIssue()
        fake_find_github_issue.return_value = github_issue
        fake_add_label.side_effect = Exception("An exception")
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)


class TestMissingSetting(unittest.TestCase):
    "test do_activity() if required setting not defined"

    def setUp(self):
        self.github_token = settings_mock.github_token

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.github_token = self.github_token

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.github_token
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # invoke
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            ("AddPreprintIssueLabel, github_token in settings is missing, skipping"),
        )


class TestMissingGithubTokenSetting(unittest.TestCase):
    "test if required github taken setting not defined"

    def setUp(self):
        self.github_token = settings_mock.github_token

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.github_token = self.github_token

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.github_token
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # invoke
        result = activity_object.check_required_settings()
        # check assertions
        self.assertEqual(result, "github_token in settings is missing, skipping")


class TestBlankGithubTokenSetting(unittest.TestCase):
    "test if required github taken setting is blank"

    def setUp(self):
        self.github_token = settings_mock.github_token

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.github_token = self.github_token

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.github_token = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # invoke
        result = activity_object.check_required_settings()
        # check assertions
        self.assertEqual(result, "github_token in settings is blank, skipping")


class TestMissingRepoNameSetting(unittest.TestCase):
    "test if required repo name setting not defined"

    def setUp(self):
        self.preprint_issues_repo_name = settings_mock.preprint_issues_repo_name

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.preprint_issues_repo_name = self.preprint_issues_repo_name

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.preprint_issues_repo_name
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # invoke
        result = activity_object.check_required_settings()
        # check assertions
        self.assertEqual(
            result, "preprint_issues_repo_name in settings is missing, skipping"
        )


class TestBlankRepoNameSetting(unittest.TestCase):
    "test if required repo name setting is blank"

    def setUp(self):
        self.preprint_issues_repo_name = settings_mock.preprint_issues_repo_name

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.preprint_issues_repo_name = self.preprint_issues_repo_name

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.preprint_issues_repo_name = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # invoke
        result = activity_object.check_required_settings()
        # check assertions
        self.assertEqual(
            result, ("preprint_issues_repo_name in settings is blank, skipping")
        )
