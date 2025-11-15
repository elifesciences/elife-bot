import os
import glob
import json
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider
import activity.activity_FindNewDocmaps as activity_module
from activity.activity_FindNewDocmaps import (
    activity_FindNewDocmaps as activity_class,
)
from tests.classes_mock import (
    FakeSMTPServer,
)
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeSession,
    FakeStorageContext,
    FakeSQSClient,
    FakeSQSQueue,
)
from tests import read_fixture
from tests.activity import helpers, settings_mock


class TestFindNewDocmaps(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()
        self.run = "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"
        self.activity_data = {"run": self.run}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def populate_docmap_index_files(self, to_dir, prev_docmap_index, next_docmap_index):
        "populate the bucket folder with docmap index data and return the paths"
        docmaps_folder = "docmaps"
        prev_run_folder = "run_2024_06_27_0001"
        next_run_folder = "run_2024_06_27_0002"
        docmap_index_folder = "docmap_index"
        docmap_json_file_name = "docmap_index.json"

        prev_docmap_index_json_path = os.path.join(
            to_dir,
            docmaps_folder,
            prev_run_folder,
            docmap_index_folder,
            docmap_json_file_name,
        )
        docmap_index_json_folder = os.path.dirname(prev_docmap_index_json_path)
        os.makedirs(docmap_index_json_folder, exist_ok=True)
        with open(prev_docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(prev_docmap_index))

        next_docmap_index_json_path = os.path.join(
            to_dir,
            docmaps_folder,
            next_run_folder,
            docmap_index_folder,
            docmap_json_file_name,
        )
        docmap_index_json_folder = os.path.dirname(next_docmap_index_json_path)
        os.makedirs(docmap_index_json_folder, exist_ok=True)
        with open(next_docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(next_docmap_index))

        resources = [
            "%s/" % docmaps_folder,
            "%s/%s/" % (docmaps_folder, prev_run_folder),
            "%s/%s/%s/" % (docmaps_folder, prev_run_folder, docmap_index_folder),
            "%s/%s/%s/%s"
            % (
                docmaps_folder,
                prev_run_folder,
                docmap_index_folder,
                docmap_json_file_name,
            ),
            "%s/%s/" % (docmaps_folder, next_run_folder),
            "%s/%s/%s/" % (docmaps_folder, next_run_folder, docmap_index_folder),
            "%s/%s/%s/%s"
            % (
                docmaps_folder,
                next_run_folder,
                docmap_index_folder,
                docmap_json_file_name,
            ),
        ]
        return resources

    @patch("boto3.client")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_do_activity_session(
        self,
        fake_clean_tmp_dir,
        fake_session,
        fake_find_github_issues,
        fake_storage_context,
        fake_email_smtp_connect,
        fake_sqs_client,
    ):
        "test when docmap index data is available from the session"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_session.return_value = FakeSession(
            {
                "run": self.run,
                "new_run_docmap_index_resource": (
                    "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0002/"
                    "docmap_index/docmap_index.json"
                ),
                "prev_run_docmap_index_resource": (
                    "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0001/"
                    "docmap_index/docmap_index.json"
                ),
            }
        )
        fake_find_github_issues.return_value = [FakeGithubIssue()]

        # remove the published dates from JSON
        docmap_json_for_84364 = json.loads(read_fixture("sample_docmap_for_84364.json"))
        del docmap_json_for_84364["steps"]["_:b2"]["actions"][0]["outputs"][0][
            "published"
        ]
        docmap_json_for_87445 = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del docmap_json_for_87445["steps"]["_:b5"]["actions"][0]["outputs"][0][
            "published"
        ]

        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # populate the bucket previous folder file paths and files
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del prev_docmap_json["steps"]["_:b3"]
        del prev_docmap_json["steps"]["_:b4"]
        prev_docmap_index = {"docmaps": [prev_docmap_json]}
        next_docmap_index = {
            "docmaps": [
                docmap_json_for_84364,
                docmap_json_for_87445,
            ]
        }
        resources = self.populate_docmap_index_files(
            directory.path, prev_docmap_index, next_docmap_index
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        expected_result = True
        expected_statuses = {
            "generate": True,
            "activity": True,
            "email": True,
        }
        expected_email_subject = "FindNewDocmaps Success! files: 2,"
        expected_email_body_contains = [
            r"FindNewDocmaps status:\n\nSuccess!\n\nactivity_status: True",
            (
                r"Version DOI with MECA file to ingest:\n"
                r"10.7554/eLife.84364.1\n"
                r"10.7554/eLife.87445.2\n\n"
            ),
        ]

        # do the activity
        result = self.activity.do_activity(self.activity_data)

        # check assertions
        self.assertEqual(result, expected_result)

        # check statuses assertions
        for status_name in [
            "generate",
            "activity",
            "email",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = expected_statuses.get(status_name)
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                ),
            )

        # check assertions on email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)
        # can make assertions on the first email
        first_email_content = None
        with open(email_files[0], encoding="utf-8") as open_file:
            first_email_content = open_file.read()
        if first_email_content:
            self.assertTrue(expected_email_subject in first_email_content)
            body = helpers.body_from_multipart_email_string(first_email_content)
            # print(body.decode("utf-8"))
            for expected_to_contain in expected_email_body_contains:
                self.assertTrue(expected_to_contain in str(body))

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_no_new_version_doi(
        self,
        fake_clean_tmp_dir,
        fake_session,
        fake_storage_context,
    ):
        "test if no new version DOI to ingest MECA are found"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        fake_session.return_value = FakeSession(
            {
                "run": self.run,
                "new_run_docmap_index_resource": (
                    "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0002/"
                    "docmap_index/docmap_index.json"
                ),
                "prev_run_docmap_index_resource": (
                    "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0001/"
                    "docmap_index/docmap_index.json"
                ),
            }
        )

        # populate the bucket previous folder file paths and files
        prev_docmap_index = {
            "docmaps": [json.loads(read_fixture("sample_docmap_for_87445.json"))]
        }
        next_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }

        resources = self.populate_docmap_index_files(
            directory.path, prev_docmap_index, next_docmap_index
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        expected_result = True
        expected_statuses = {
            "generate": True,
            "upload": None,
            "activity": True,
            "email": None,
        }

        # do the activity
        result = self.activity.do_activity(self.activity_data)

        # check assertions
        self.assertEqual(result, expected_result)

        # check statuses assertions
        for status_name in [
            "generate",
            "upload",
            "activity",
            "email",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = expected_statuses.get(status_name)
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                ),
            )

        # assert output bucket contents contains the new docmap index
        self.assertEqual(
            sorted(os.listdir(os.path.join(directory.path, "docmaps"))),
            ["run_2024_06_27_0001", "run_2024_06_27_0002"],
        )


class TestSendAdminEmail(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()

        class FakeSettings:
            def __init__(self):
                for attr in [
                    "domain",
                    "downstream_recipients_yaml",
                    "poa_packaging_bucket",
                    "ses_poa_sender_email",
                ]:
                    setattr(self, attr, getattr(settings_mock, attr, None))

        settings_object = FakeSettings()
        # email recipients is a list
        settings_object.ses_admin_email = ["one@example.org", "two@example.org"]

        self.activity = activity_class(settings_object, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_send_admin_email(self, fake_email_smtp_connect):
        "test for when the email recipients is a list"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        self.activity.statuses["activity"] = True
        new_meca_version_dois = ["10.7554/eLife.87445.2"]
        expected_result = True
        expected_email_count = 2
        expected_email_subject = "FindNewDocmaps Success! files: 1,"
        expected_email_from = "From: sender@example.org"
        expected_email_body_contains = [
            r"FindNewDocmaps status:\n\nSuccess!\n\nactivity_status: True",
            r"Version DOI with MECA file to ingest:\n10.7554/eLife.87445.2\n\n",
        ]

        result = self.activity.send_admin_email(new_meca_version_dois)
        self.assertEqual(result, expected_result)

        # check assertions on email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)

        self.assertEqual(len(email_files), expected_email_count)
        # can look at the first email for the subject and sender
        first_email_content = None
        with open(email_files[0], encoding="utf-8") as open_file:
            first_email_content = open_file.read()
        if first_email_content:
            self.assertTrue(expected_email_subject in first_email_content)
            self.assertTrue(expected_email_from in first_email_content)
            body = helpers.body_from_multipart_email_string(first_email_content)
            # print(body.decode("utf-8"))
            for expected_to_contain in expected_email_body_contains:
                self.assertTrue(expected_to_contain in str(body))
