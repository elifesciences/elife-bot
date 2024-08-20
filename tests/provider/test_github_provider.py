import unittest
from mock import patch
from provider import github_provider
from tests import settings_mock
from tests.activity.classes_mock import (
    FakeGithub,
    FakeGithubIssue,
    FakeGithubRepository,
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
        result = github_provider.find_github_issue(settings_mock.github_token, settings_mock.preprint_issues_repo_name, version_doi)
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
        result = github_provider.find_github_issue(settings_mock.github_token, settings_mock.preprint_issues_repo_name, version_doi)
        # assert
        self.assertEqual(result, None)
