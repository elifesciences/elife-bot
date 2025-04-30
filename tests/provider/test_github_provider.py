import unittest
from mock import patch
from github import GithubException
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


@patch.object(github_provider, "Github")
class TestUpdateGithub(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_no_changes_to_file_str(self, mock_github):
        repo_file = "file.txt"
        # utf-8 string content
        content = "<article/>"
        mock_github.return_value = FakeGithub()
        result = github_provider.update_github(
            settings_mock, self.logger, repo_file, content
        )
        self.assertEqual(result, "No changes in file %s" % repo_file)

    def test_no_changes_to_file_bytes(self, mock_github):
        repo_file = "file.txt"
        # bytestring content
        content = b"<article/>"
        mock_github.return_value = FakeGithub()
        result = github_provider.update_github(
            settings_mock, self.logger, repo_file, content
        )
        self.assertEqual(result, "No changes in file %s" % repo_file)

    def test_updated_file(self, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        result = github_provider.update_github(
            settings_mock, self.logger, repo_file, content
        )
        self.assertEqual(
            result, "File %s successfully updated. Commit: None" % repo_file
        )

    @patch.object(FakeGithubRepository, "get_contents")
    def test_get_contents_exception(self, fake_get_contents, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_get_contents.side_effect = GithubException(
            status="status", data="data", headers="headers"
        )
        result = github_provider.update_github(
            settings_mock, self.logger, repo_file, content
        )
        self.assertEqual(result, "File %s successfully added. Commit: None" % repo_file)

    @patch.object(FakeGithubRepository, "get_contents")
    def test_get_contents_unhandled_exception(self, fake_get_contents, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_get_contents.side_effect = Exception("An unhanded exception")
        with self.assertRaises(Exception):
            github_provider.update_github(
                settings_mock, self.logger, repo_file, content
            )
        self.assertEqual(
            self.logger.loginfo[-1],
            "Exception: file %s. Error: An unhanded exception" % repo_file,
        )

    @patch.object(FakeGithubRepository, "create_file")
    @patch.object(FakeGithubRepository, "get_contents")
    def test_create_file_exception(
        self, fake_get_contents, fake_create_file, mock_github
    ):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_get_contents.side_effect = GithubException(
            status="status", data="data", headers="headers"
        )
        fake_create_file.side_effect = GithubException(
            status=409, data="data", headers="headers"
        )
        with self.assertRaises(Exception):
            github_provider.update_github(
                settings_mock, self.logger, repo_file, content
            )
        self.assertEqual(
            self.logger.logwarning, 'Retrying because of exception: 409 "data"'
        )

    @patch.object(FakeGithubRepository, "update_file")
    def test_update_file_exception(self, fake_update_file, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_update_file.side_effect = GithubException(
            status=409, data="data", headers="headers"
        )
        with self.assertRaises(Exception):
            github_provider.update_github(
                settings_mock, self.logger, repo_file, content
            )
        self.assertEqual(
            self.logger.logwarning, 'Retrying because of exception: 409 "data"'
        )

    @patch.object(FakeGithubRepository, "update_file")
    def test_update_file_exception_unhandled_status(
        self, fake_update_file, mock_github
    ):
        "test for status 500 which currently does not result in a retry"
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_update_file.side_effect = GithubException(
            status=500, data="data", headers="headers"
        )
        with self.assertRaises(GithubException):
            github_provider.update_github(
                settings_mock, self.logger, repo_file, content
            )
