import os
import json
from datetime import datetime
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import utils
import activity.activity_DownloadDocmapIndex as activity_module
from activity.activity_DownloadDocmapIndex import (
    activity_DownloadDocmapIndex as activity_class,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests import read_fixture
from tests.activity import settings_mock


class TestDownloadDocmapIndex(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()
        self.activity_data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch("provider.docmap_provider.requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_session,
        fake_datetime,
        fake_storage_context,
        fake_get,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
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

        # populate the bucket previous folder file paths and files
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        sample_prev_docmap_index = {"docmaps": [prev_docmap_json]}
        prev_docmap_index_json_path = os.path.join(
            directory.path,
            "docmaps",
            "run_2024_06_27_0001",
            "docmap_index",
            "docmap_index.json",
        )
        docmap_index_json_folder = os.path.dirname(prev_docmap_index_json_path)
        os.makedirs(docmap_index_json_folder, exist_ok=True)
        with open(prev_docmap_index_json_path, "w", encoding="utf-8") as open_file:
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
            "upload": True,
            "activity": True,
        }

        # do the activity
        result = self.activity.do_activity(self.activity_data)

        # check assertions
        self.assertEqual(result, expected_result)

        # check statuses assertions
        for status_name in [
            "upload",
            "activity",
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
        with open(prev_docmap_index_json_path, "r", encoding="utf-8") as open_file:
            self.assertEqual(json.loads(open_file.read()), sample_prev_docmap_index)

        # assert session values
        self.assertEqual(
            mock_session.get_value("prev_run_docmap_index_resource"),
            "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0001/docmap_index/docmap_index.json",
        )
        self.assertEqual(
            mock_session.get_value("new_run_docmap_index_resource"),
            "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0002/docmap_index/docmap_index.json",
        )

        # assert output bucket contents contains the new docmap index
        self.assertEqual(
            sorted(os.listdir(os.path.join(directory.path, "docmaps"))),
            ["run_2024_06_27_0001", "run_2024_06_27_0002"],
        )

    @patch("provider.docmap_provider.get_docmap_index_json")
    @patch.object(activity_module, "get_session")
    def test_docmap_index_exception(
        self,
        fake_session,
        fake_get_docmap_index,
    ):
        "test if an exception is raised getting docmap index"
        fake_session.return_value = FakeSession({})
        fake_get_docmap_index.side_effect = Exception("")
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("provider.docmap_provider.get_docmap_index_json")
    @patch.object(activity_module, "get_session")
    def test_docmap_index_none(
        self,
        fake_session,
        fake_get_docmap_index,
    ):
        "test if docmap index is None"
        fake_session.return_value = FakeSession({})
        fake_get_docmap_index.return_value = None
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("provider.docmap_provider.get_docmap_index_json")
    @patch.object(activity_module, "get_session")
    def test_docmap_index_empty(
        self,
        fake_session,
        fake_get_docmap_index,
    ):
        "test if docmap index is an empty list"
        fake_session.return_value = FakeSession({})
        fake_get_docmap_index.return_value = {"docmaps": []}
        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)


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
            "DownloadDocmapIndex, docmap_index_url in settings is missing, skipping",
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
            "DownloadDocmapIndex, docmap_index_url in settings is blank, skipping",
        )


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
