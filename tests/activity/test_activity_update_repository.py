import unittest
from ssl import SSLError
from github import GithubException
from mock import patch, MagicMock
from activity.activity_UpdateRepository import activity_UpdateRepository, RetryException
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeStorageContext, FakeLogger, FakeLaxProvider


class FakeGithub:
    "mock object for github.Github"

    def get_user(self, login):
        return FakeGithubNamedUser()


class FakeGithubNamedUser:
    "mock object for github.NamedUser.NamedUser"

    def get_repo(self, full_name_or_id):
        return FakeGithubRepository()


class FakeGithubRepository:
    "mock object for github.Repository.Repository"

    def get_contents(self, path):
        return FakeGithubContentFile()

    def update_file(
        self, path, message, content, sha, branch=None, committer=None, author=None
    ):
        pass

    def create_file(path, message, content, branch=None, committer=None, author=None):
        pass


class FakeGithubContentFile:
    "mock object for github.ContentFile.ContentFile"

    def __init__(self):
        self.decoded_content = b"<article/>"
        self.sha = "sha"


@patch("activity.activity_UpdateRepository.provider")
@patch("activity.activity_UpdateRepository.storage_context")
@patch("dashboard_queue.send_message")
class TestUpdateRepository(unittest.TestCase):
    def test_happy_path(self, dashboard_queue, mock_storage_context, provider):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        activity_object.update_github = MagicMock()

        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, True)

    def test_missing_settings_value(
        self, dashboard_queue, mock_storage_context, provider
    ):
        "test for when settings values are None depending on the environment name"

        class ci:
            "mock settings object for testing"
            domain = None
            default_task_list = None
            git_repo_path = None
            git_repo_name = None
            github_token = None

        class end2end(ci):
            pass

        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider

        # test ci environment
        activity_object = activity_UpdateRepository(ci, FakeLogger())
        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, True)

        # test end2end environment
        activity_object = activity_UpdateRepository(end2end, FakeLogger())
        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, "ActivityPermanentFailure")

    def test_retry_exception_leads_to_a_retry(
        self, dashboard_queue, mock_storage_context, provider
    ):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        activity_object.update_github = MagicMock()

        activity_object.update_github.side_effect = RetryException("Retry")

        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, "ActivityTemporaryFailure")

    def test_ssl_timeout_error_leads_to_a_retry(
        self, dashboard_queue, mock_storage_context, provider
    ):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        activity_object.update_github = MagicMock()

        activity_object.update_github.side_effect = SSLError(
            "The read operation timed out"
        )

        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, "ActivityTemporaryFailure")

    def test_ssl_timeout_error_leads_to_a_permanent_failure(
        self, dashboard_queue, mock_storage_context, provider
    ):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        activity_object.update_github = MagicMock()

        activity_object.update_github.side_effect = SSLError("Unhandled error message")

        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, "ActivityPermanentFailure")

    def test_generic_errors_we_dont_know_how_to_treat_lead_to_permanent_failures(
        self, dashboard_queue, mock_storage_context, provider
    ):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        activity_object.update_github = MagicMock()

        activity_object.update_github.side_effect = RuntimeError(
            "One of the cross beams has gone out askew..."
        )

        result = activity_object.do_activity(
            {
                "article_id": "12345",
                "version": 1,
                "run": "123abc",
            }
        )
        self.assertEqual(result, "ActivityPermanentFailure")


@patch("activity.activity_UpdateRepository.Github")
class TestUpdateGithub(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_no_changes_to_file(self, mock_github):
        repo_file = "file.txt"
        content = b"<article/>"
        mock_github.return_value = FakeGithub()
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        result = activity_object.update_github(repo_file, content)
        self.assertEqual(result, "No changes in file %s" % repo_file)

    def test_updated_file(self, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        result = activity_object.update_github(repo_file, content)
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
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        result = activity_object.update_github(repo_file, content)
        self.assertEqual(result, "File %s successfully added. Commit: None" % repo_file)

    @patch.object(FakeGithubRepository, "get_contents")
    def test_get_contents_unhandled_exception(self, fake_get_contents, mock_github):
        repo_file = "file.txt"
        content = b"<article>Updated</article>"
        mock_github.return_value = FakeGithub()
        fake_get_contents.side_effect = Exception("An unhanded exception")
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        with self.assertRaises(Exception):
            activity_object.update_github(repo_file, content)
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
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        with self.assertRaises(Exception):
            activity_object.update_github(repo_file, content)
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
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        with self.assertRaises(Exception):
            activity_object.update_github(repo_file, content)
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
        activity_object = activity_UpdateRepository(settings_mock, self.logger)
        with self.assertRaises(GithubException):
            activity_object.update_github(repo_file, content)
