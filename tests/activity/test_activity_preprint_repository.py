import unittest
from ssl import SSLError
from mock import patch, MagicMock
from testfixtures import TempDirectory
from provider import github_provider
import activity.activity_PreprintRepository as activity_module
from activity.activity_PreprintRepository import (
    activity_PreprintRepository as activity_class,
)
from activity.activity_PreprintRepository import RetryException
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeSession,
    FakeStorageContext,
    FakeLogger,
)

SESSION_DICT = test_activity_data.post_preprint_publication_session_example()


@patch.object(activity_module, "storage_context")
@patch.object(activity_module, "get_session")
class TestPreprintRepository(unittest.TestCase):
    def setUp(self):
        self.update_github_original = github_provider.update_github

    def tearDown(self):
        TempDirectory.cleanup_all()
        # reset the mocked method
        github_provider.update_github = self.update_github_original

    def test_happy_path(self, fake_session, mock_storage_context):
        directory = TempDirectory()

        activity_object = activity_class(settings_mock, FakeLogger())

        fake_session.return_value = FakeSession(SESSION_DICT)
        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )
        mock_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        github_provider.update_github = MagicMock()

        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, True)

        self.assertTrue(
            (
                "PreprintRepository, for 10.7554/eLife.95901.2"
                " downloading s3://bot_bucket/expanded_meca/95901-v2/"
                "1ee54f9a-cb28-4c8e-8232-4b317cf4beda/expanded_files/content/24301711.xml"
                " and adding to git repo path preprints/elife-preprint-95901-v2.xml"
            )
            in activity_object.logger.loginfo
        )

    def test_missing_settings_value(self, fake_session, mock_storage_context):
        "test for when settings values are None depending on the environment name"

        class ci:
            "mock settings object for testing"
            domain = None
            default_task_list = None
            git_preprint_repo_path = None
            git_repo_name = None
            github_token = None

        class end2end(ci):
            pass

        fake_session.return_value = FakeSession(
            test_activity_data.post_preprint_publication_session_example()
        )
        mock_storage_context.return_value = FakeStorageContext()

        # test ci environment
        activity_object = activity_class(ci, FakeLogger())
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, True)

        # test end2end environment
        activity_object = activity_class(end2end, FakeLogger())
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, "ActivityPermanentFailure")

    def test_retry_exception_leads_to_a_retry(self, fake_session, mock_storage_context):
        activity_object = activity_class(settings_mock, FakeLogger())
        fake_session.return_value = FakeSession(
            test_activity_data.post_preprint_publication_session_example()
        )
        mock_storage_context.return_value = FakeStorageContext()
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = RetryException("Retry")

        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    def test_ssl_timeout_error_leads_to_a_retry(
        self, fake_session, mock_storage_context
    ):
        activity_object = activity_class(settings_mock, FakeLogger())
        fake_session.return_value = FakeSession(
            test_activity_data.post_preprint_publication_session_example()
        )
        mock_storage_context.return_value = FakeStorageContext()
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = SSLError(
            "The read operation timed out"
        )

        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    def test_ssl_timeout_error_leads_to_a_permanent_failure(
        self, fake_session, mock_storage_context
    ):
        activity_object = activity_class(settings_mock, FakeLogger())
        fake_session.return_value = FakeSession(
            test_activity_data.post_preprint_publication_session_example()
        )
        mock_storage_context.return_value = FakeStorageContext()
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = SSLError("Unhandled error message")

        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, "ActivityPermanentFailure")

    def test_generic_errors_we_dont_know_how_to_treat_lead_to_permanent_failures(
        self, fake_session, mock_storage_context
    ):
        activity_object = activity_class(settings_mock, FakeLogger())
        fake_session.return_value = FakeSession(
            test_activity_data.post_preprint_publication_session_example()
        )
        mock_storage_context.return_value = FakeStorageContext()
        github_provider.update_github = MagicMock()

        github_provider.update_github.side_effect = RuntimeError(
            "One of the cross beams has gone out askew..."
        )

        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, "ActivityPermanentFailure")
