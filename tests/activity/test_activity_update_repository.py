import unittest
from ssl import SSLError
from mock import patch, MagicMock
from provider import github_provider
from activity.activity_UpdateRepository import activity_UpdateRepository, RetryException
from tests.activity import settings_mock
from tests.activity.classes_mock import (
    FakeStorageContext,
    FakeLogger,
    FakeLaxProvider,
)


@patch("activity.activity_UpdateRepository.provider")
@patch("activity.activity_UpdateRepository.storage_context")
@patch("dashboard_queue.send_message")
class TestUpdateRepository(unittest.TestCase):
    def setUp(self):
        self.update_github_original = github_provider.update_github

    def tearDown(self):
        # reset the mocked method
        github_provider.update_github = self.update_github_original

    def test_happy_path(self, dashboard_queue, mock_storage_context, provider):
        activity_object = activity_UpdateRepository(settings_mock, FakeLogger())
        dashboard_queue.return_value = True
        mock_storage_context.return_value = FakeStorageContext()
        provider.lax_provider = FakeLaxProvider
        github_provider.update_github = MagicMock()

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
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = RetryException("Retry")

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
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = SSLError(
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
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = SSLError("Unhandled error message")

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
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = RuntimeError(
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
