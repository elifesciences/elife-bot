import os
import glob
import json
from datetime import datetime
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import utils
import activity.activity_FindNewDocmaps as activity_module
from activity.activity_FindNewDocmaps import (
    activity_FindNewDocmaps as activity_class,
)
from tests.classes_mock import (
    FakeSMTPServer,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
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
        self.activity_data = {}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch("boto3.client")
    @patch("provider.docmap_provider.requests.get")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_datetime,
        fake_storage_context,
        fake_email_smtp_connect,
        fake_get,
        fake_sqs_client,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )

        # remove the published dates from JSON
        docmap_json_for_84364 = json.loads(read_fixture("sample_docmap_for_84364.json"))
        del docmap_json_for_84364["steps"]["_:b2"]["actions"][0]["outputs"][0][
            "published"
        ]
        docmap_json_for_87445 = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del docmap_json_for_87445["steps"]["_:b5"]["actions"][0]["outputs"][0][
            "published"
        ]
        sample_docmap_index = {
            "docmaps": [
                docmap_json_for_84364,
                docmap_json_for_87445,
            ]
        }

        fake_get.return_value = FakeResponse(
            200, content=json.dumps(sample_docmap_index)
        )
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # populate the bucket previous folder file paths and files
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del prev_docmap_json["steps"]["_:b3"]
        del prev_docmap_json["steps"]["_:b4"]
        sample_prev_docmap_index = {"docmaps": [prev_docmap_json]}
        docmap_index_json_path = os.path.join(
            directory.path,
            "docmaps",
            "run_2024_06_27_0001",
            "docmap_index",
            "docmap_index.json",
        )
        docmap_index_json_folder = os.path.dirname(docmap_index_json_path)
        os.makedirs(docmap_index_json_folder, exist_ok=True)
        with open(docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(sample_prev_docmap_index))
        resources = [
            "docmaps/",
            "docmaps/run_2024_06_27_0001/",
            "docmaps/run_2024_06_27_0001/docmap_index/",
            "docmaps/run_2024_06_27_0001/docmap_index/docmap_index.json",
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        expected_result = True
        expected_statuses = {
            "generate": True,
            "upload": True,
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
        # assert previous docmap index JSON file details
        self.assertEqual(os.listdir(docmap_index_json_folder), ["docmap_index.json"])
        with open(docmap_index_json_path, "r", encoding="utf-8") as open_file:
            self.assertEqual(json.loads(open_file.read()), sample_prev_docmap_index)

        # assert input folder contents
        self.assertEqual(
            os.listdir(os.path.join(self.activity.get_tmp_dir(), "input_dir")),
            ["prev_docmap_index.json"],
        )
        # assert output bucket contents contains the new docmap index
        self.assertEqual(
            sorted(os.listdir(os.path.join(directory.path, "docmaps"))),
            ["run_2024_06_27_0001", "run_2024_06_27_0002"],
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

    @patch("provider.docmap_provider.requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_no_new_version_doi(
        self,
        fake_clean_tmp_dir,
        fake_datetime,
        fake_storage_context,
        fake_get,
    ):
        "test if no new version DOI to ingest MECA are found"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )

        sample_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }

        fake_get.return_value = FakeResponse(
            200, content=json.dumps(sample_docmap_index)
        )

        # populate the bucket previous folder file paths and files
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        sample_prev_docmap_index = {"docmaps": [prev_docmap_json]}
        docmap_index_json_path = os.path.join(
            directory.path,
            "docmaps",
            "run_2024_06_27_0001",
            "docmap_index",
            "docmap_index.json",
        )
        docmap_index_json_folder = os.path.dirname(docmap_index_json_path)
        os.makedirs(docmap_index_json_folder, exist_ok=True)
        with open(docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(sample_prev_docmap_index))
        resources = [
            "docmaps/",
            "docmaps/run_2024_06_27_0001/",
            "docmaps/run_2024_06_27_0001/docmap_index/",
            "docmaps/run_2024_06_27_0001/docmap_index/docmap_index.json",
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        expected_result = True
        expected_statuses = {
            "generate": True,
            "upload": True,
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
        # assert previous docmap index JSON file details
        self.assertEqual(os.listdir(docmap_index_json_folder), ["docmap_index.json"])
        with open(docmap_index_json_path, "r", encoding="utf-8") as open_file:
            self.assertEqual(json.loads(open_file.read()), sample_prev_docmap_index)

        # assert input folder contents
        self.assertEqual(
            os.listdir(os.path.join(self.activity.get_tmp_dir(), "input_dir")),
            ["prev_docmap_index.json"],
        )
        # assert output bucket contents contains the new docmap index
        self.assertEqual(
            sorted(os.listdir(os.path.join(directory.path, "docmaps"))),
            ["run_2024_06_27_0001", "run_2024_06_27_0002"],
        )

    @patch("provider.docmap_provider.get_docmap_index_json")
    def test_docmap_index_exception(
        self,
        fake_get_docmap_index,
    ):
        "test if an exception is raised getting docmap index"
        fake_get_docmap_index.side_effect = Exception("")
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch("provider.docmap_provider.get_docmap_index_json")
    def test_docmap_index_none(
        self,
        fake_get_docmap_index,
    ):
        "test if docmap index is None"
        fake_get_docmap_index.return_value = None
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch("provider.docmap_provider.get_docmap_index_json")
    def test_docmap_index_empty(
        self,
        fake_get_docmap_index,
    ):
        "test if docmap index is an empty list"
        fake_get_docmap_index.return_value = {"docmaps": []}
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)


class TestMissingSettings(unittest.TestCase):
    def setUp(self):
        self.docmap_index_url = settings_mock.docmap_index_url

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.docmap_index_url = self.docmap_index_url

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.docmap_index_url
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, True)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "FindNewDocmaps, docmap_index_url in settings is missing, skipping",
        )


class TestBlankSettings(unittest.TestCase):
    def setUp(self):
        self.docmap_index_url = settings_mock.docmap_index_url

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.docmap_index_url = self.docmap_index_url

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.docmap_index_url = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, True)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "FindNewDocmaps, docmap_index_url in settings is blank, skipping",
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


class TestDateFromRunFolder(unittest.TestCase):
    "tests for date_from_run_folder()"

    def test_date(self):
        "test a run folder name"
        folder_name = "run_2024_07_27_0001"
        expected = datetime.strptime("2024-07-27 +0000", "%Y-%m-%d %z")
        result = activity_module.date_from_run_folder(folder_name)
        self.assertEqual(result, expected)

    def test_no_date(self):
        "test a folder name containing no date"
        folder_name = "run"
        with self.assertRaises(ValueError):
            activity_module.date_from_run_folder(folder_name)

    def test_blank(self):
        "test blank string value"
        folder_name = ""
        with self.assertRaises(ValueError):
            activity_module.date_from_run_folder(folder_name)

    def test_none(self):
        "test None value"
        folder_name = None
        with self.assertRaises(AttributeError):
            activity_module.date_from_run_folder(folder_name)


class TestRunFolderNames(unittest.TestCase):
    "tests for run_folder_names()"

    @patch.object(FakeStorageContext, "list_resources")
    def test_run_folder_names(self, fake_list_resources):
        fake_storage = FakeStorageContext()
        fake_list_resources.return_value = [
            "foo/",
            "foo/bar.txt",
            "docmaps/foo/bar.txt",
            "docmaps/run_2024_06_26_0001/docmap_index/docmap_index.json",
            "docmaps/run_2024_06_26_0002/docmap_index/docmap_index.json",
            "docmaps/run_2024_06_27_0001/docmap_index/docmap_index.json",
        ]
        bucket_path = "s3://poa_packaging_bucket/docmaps/"
        expected = [
            "run_2024_06_26_0001",
            "run_2024_06_26_0002",
            "run_2024_06_27_0001",
        ]
        result = activity_module.run_folder_names(fake_storage, bucket_path)
        self.assertEqual(result, expected)

    @patch.object(FakeStorageContext, "list_resources")
    def test_run_folder_names_empty(self, fake_list_resources):
        "test if no previous run folder names are found"
        fake_storage = FakeStorageContext()
        fake_list_resources.return_value = []
        bucket_path = "s3://poa_packaging_bucket/docmaps/"
        expected = []
        result = activity_module.run_folder_names(fake_storage, bucket_path)
        self.assertEqual(result, expected)


class TestNewRunFolder(unittest.TestCase):
    "tests for new_run_folder()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "run_folder_names")
    def test_new_run_folder(self, fake_run_folder_names, fake_datetime):
        "test new folder name for first folder of the day"
        directory = TempDirectory()
        fake_run_folder_names.return_value = ["run_2024_06_16_0001"]
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        fake_datetime.return_value = datetime.strptime(
            "2024-06-17 +0000", "%Y-%m-%d %z"
        )
        expected = "run_2024_06_17_0001"
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.new_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "run_folder_names")
    def test_new_run_folder_increment(self, fake_run_folder_names, fake_datetime):
        "test new folder name for the same day"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_16_0001",
            "run_2024_06_27_0001",
            "run_2024_06_27_0002",
        ]
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )
        expected = "run_2024_06_27_0003"
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.new_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "run_folder_names")
    def test_new_run_folder_first(self, fake_run_folder_names, fake_datetime):
        "test new folder name if there are no previous run folder names"
        directory = TempDirectory()
        fake_run_folder_names.return_value = []
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        fake_datetime.return_value = datetime.strptime(
            "2024-06-17 +0000", "%Y-%m-%d %z"
        )
        expected = "run_2024_06_17_0001"
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.new_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, expected)


class TestPreviousRunFolder(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "run_folder_names")
    def test_previous_run_folder(self, fake_run_folder_names):
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_16_0001",
            "run_2024_06_27_0001",
            "run_2024_06_27_0002",
        ]
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, "run_2024_06_27_0002")

    @patch.object(activity_module, "run_folder_names")
    def test_no_run_folders(self, fake_run_folder_names):
        "test if list of run folders is empty"
        directory = TempDirectory()
        fake_run_folder_names.return_value = []
        expected = None
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, expected)

    @patch.object(activity_module, "run_folder_names")
    def test_previous_run_folder_one(self, fake_run_folder_names):
        "test one run folder only"
        directory = TempDirectory()
        fake_run_folder_names.return_value = ["run_2024_06_17_0001"]
        from_folder = ""
        expected = "run_2024_06_17_0001"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(
            fake_storage, bucket_path, from_folder
        )
        self.assertEqual(result, expected)

    @patch.object(activity_module, "run_folder_names")
    def test_run_number(self, fake_run_folder_names):
        "test run folders by number"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_17_0001",
            "run_2024_06_17_0002",
            "run_2024_06_17_0003",
        ]
        expected = "run_2024_06_17_0003"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(fake_storage, bucket_path)
        self.assertEqual(result, expected)

    @patch.object(activity_module, "run_folder_names")
    def test_from_folder(self, fake_run_folder_names):
        "test supplying from_folder argument"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_17_0001",
            "run_2024_06_17_0002",
            "run_2024_06_17_0003",
        ]
        from_folder = "run_2024_06_17_0002"
        expected = "run_2024_06_17_0001"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(
            fake_storage, bucket_path, from_folder
        )
        self.assertEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "run_folder_names")
    def test_complicated_one(self, fake_run_folder_names, fake_datetime):
        "test assorted folder names with gap between the dates"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_14_0001",
            "run_2024_06_14_0002",
            "run_2024_06_17_0001",
        ]
        fake_datetime.return_value = datetime.strptime(
            "2024-06-15 +0000", "%Y-%m-%d %z"
        )
        from_folder = None
        expected = "run_2024_06_14_0002"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(
            fake_storage, bucket_path, from_folder
        )
        self.assertEqual(result, expected)

    @patch.object(activity_module, "run_folder_names")
    def test_complicated_two(self, fake_run_folder_names):
        "test assorted folder names and from_folder not found in the list"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_14_0001",
            "run_2024_06_14_0002",
            "run_2024_06_17_0001",
        ]
        from_folder = "run_2024_06_15_0005"
        expected = "run_2024_06_14_0002"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(
            fake_storage, bucket_path, from_folder
        )
        self.assertEqual(result, expected)

    @patch.object(activity_module, "run_folder_names")
    def test_future_from_folder(self, fake_run_folder_names):
        "test a from_folder argument value greater than dates found in the folder list"
        directory = TempDirectory()
        fake_run_folder_names.return_value = [
            "run_2024_06_17_0001",
            "run_2024_06_17_0002",
            "run_2024_06_17_0003",
        ]
        from_folder = "run_2024_06_20_0001"
        expected = "run_2024_06_17_0003"
        fake_storage = FakeStorageContext(directory.path, dest_folder=directory.path)
        bucket_path = os.path.join(directory.path, "docmaps")
        result = activity_module.previous_run_folder(
            fake_storage, bucket_path, from_folder
        )
        self.assertEqual(result, expected)
