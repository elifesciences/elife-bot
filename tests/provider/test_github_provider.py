import unittest
from mock import patch
from provider import github_provider
from tests import settings_mock
from tests.activity.classes_mock import (
    FakeGithub,
    FakeGithubIssue,
    FakeGithubRepository,
    FakeLogger,
)


class TestMatchIssueTitle(unittest.TestCase):
    "tests for match_issue_title()"

    def test_match_issue_title(self):
        "test title matching article_id MSID and version"
        title = "MSID: 95901 Version: 1 DOI x"
        msid = 95901
        version = 1
        result = github_provider.match_issue_title(title, msid, version)
        self.assertEqual(result, True)

    def test_no_match(self):
        "test if the title does not match"
        title = "MSID: 5 Version: b DOI x"
        msid = 95901
        version = 1
        result = github_provider.match_issue_title(title, msid, version)
        self.assertEqual(result, False)

    def test_blank_title(self):
        "test if the title is blank"
        title = ""
        msid = 95901
        version = 1
        result = github_provider.match_issue_title(title, msid, version)
        self.assertEqual(result, False)


class TestFindGithubIssue(unittest.TestCase):
    "tests for find_github_issue()"

    @patch.object(FakeGithubRepository, "get_issues")
    @patch.object(github_provider, "Github")
    def test_find_github_issue(self, fake_github, fake_get_issues):
        "test find_github_issue matches an issue"

        fake_github.return_value = FakeGithub()
        fake_get_issues.return_value = [
            FakeGithubIssue(
                title="MSID: 96848 Version: 2 DOI: 10.1101/2024.01.31.xxxx96848",
                number=1,
            ),
            FakeGithubIssue(
                title="MSID: 95901 Version: 1 DOI: 10.1101/2024.01.31.xxxx95901",
                number=2,
            ),
        ]
        version_doi = "10.7554/eLife.95901.1"
        # invoke
        result = github_provider.find_github_issue(
            settings_mock.github_token,
            settings_mock.preprint_issues_repo_name,
            version_doi,
        )
        # assert
        self.assertIsNotNone(result)
        self.assertEqual(
            result.title, "MSID: 95901 Version: 1 DOI: 10.1101/2024.01.31.xxxx95901"
        )

    @patch.object(FakeGithubRepository, "get_issues")
    @patch.object(github_provider, "Github")
    def test_no_issue(self, fake_github, fake_get_issues):
        "test if no issue matches"
        fake_github.return_value = FakeGithub()
        fake_get_issues.return_value = []
        version_doi = "10.7554/eLife.95901.1"
        # invoke
        result = github_provider.find_github_issue(
            settings_mock.github_token,
            settings_mock.preprint_issues_repo_name,
            version_doi,
        )
        # assert
        self.assertEqual(result, None)


class TestAddGithubIssueComment(unittest.TestCase):
    "tests for add_github_issue_comment()"

    @patch.object(FakeGithubRepository, "get_issues")
    @patch.object(github_provider, "Github")
    def test_add_github_issue_comment(self, fake_github, fake_get_issues):
        "test finding and adding a Github issue comment"
        fake_github.return_value = FakeGithub()
        fake_get_issues.return_value = [
            FakeGithubIssue(
                title="MSID: 95901 Version: 1 DOI: 10.1101/2024.01.31.xxxx95901",
                number=2,
            ),
        ]
        fake_logger = FakeLogger()
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        issue_comment = "Test comment."
        github_provider.add_github_issue_comment(
            settings_mock, fake_logger, caller_name, version_doi, issue_comment
        )
        # assert
        self.assertEqual(fake_logger.loginfo, ["First logger info"])
        self.assertEqual(fake_logger.logexception, "First logger exception")

    @patch.object(FakeGithubRepository, "get_issues")
    @patch.object(github_provider, "Github")
    def test_exception(self, fake_github, fake_get_issues):
        "test exception raised when finding Github issues"
        fake_github.return_value = FakeGithub()
        exception_message = "An exception"
        fake_get_issues.side_effect = Exception(exception_message)
        fake_logger = FakeLogger()
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        issue_comment = "Test comment."
        github_provider.add_github_issue_comment(
            settings_mock, fake_logger, caller_name, version_doi, issue_comment
        )
        self.assertEqual(
            fake_logger.logexception,
            (
                (
                    "%s, exception when adding a comment to Github for version DOI %s"
                    " - Details: %s"
                )
            )
            % (caller_name, version_doi, exception_message),
        )
