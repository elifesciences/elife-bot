import os
import datetime
import json
import unittest
from mock import patch
from ddt import ddt, data
from testfixtures import TempDirectory
from provider import cleaner, preprint, utils
import activity.activity_FindNewPreprints as activity_module
from activity.activity_FindNewPreprints import (
    activity_FindNewPreprints as activity_class,
)
from tests import read_fixture
from tests.classes_mock import (
    FakeSMTPServer,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
    FakeSQSClient,
    FakeSQSQueue,
)
from tests.activity import settings_mock


@ddt
class TestFindNewPreprints(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()
        self.run = "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"
        self.activity_data = {"run": self.run}
        self.session = FakeSession(
            {
                "run": self.run,
                "new_run_docmap_index_resource": (
                    "s3://poa_packaging_bucket/docmaps/run_2024_06_27_0002/"
                    "docmap_index/docmap_index.json"
                ),
            }
        )
        # reset retry values
        cleaner.DOCMAP_SLEEP_SECONDS = 0.0001
        cleaner.DOCMAP_RETRY = 2

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def populate_docmap_index_files(self, to_dir, next_docmap_index):
        "populate the bucket folder with docmap index data and return the paths"
        docmaps_folder = "docmaps"
        next_run_folder = "run_2024_06_27_0002"
        docmap_index_folder = "docmap_index"
        docmap_json_file_name = "docmap_index.json"

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
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.download_helper.storage_context")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch("requests.get")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    @data(
        {
            "comment": "One XML to generate",
            "bucket_filenames": ["elife-preprint-92362-v1.xml"],
            "post_status_code": 200,
            "expected_result": True,
            "expected_generate_status": True,
            "expected_upload_status": True,
            "expected_activity_status": True,
            "expected_email_status": True,
            "expected_file_count": 1,
            "expected_bucket_files": ["elife-preprint-87445-v2.xml"],
        },
        {
            "comment": "No XML files to generate",
            "bucket_filenames": [
                "elife-preprint-87445-v2.xml",
                "elife-preprint-92362-v1.xml",
            ],
            "post_status_code": 200,
            "expected_result": True,
            "expected_generate_status": None,
            "expected_upload_status": None,
            "expected_activity_status": None,
            "expected_email_status": None,
            "expected_file_count": 0,
            "expected_bucket_files": [],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_session,
        fake_get_current_datetime,
        fake_get,
        fake_storage_context,
        fake_outbox_storage_context,
        fake_download_storage_context,
        fake_email_smtp_connect,
        fake_get_docmap,
        fake_sqs_client,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_session.return_value = self.session

        date_time = "2023-11-23 +0000"
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            date_time, "%Y-%m-%d %z"
        )

        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # populate the bucket previous folder file paths and files
        next_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        resources = self.populate_docmap_index_files(directory.path, next_docmap_index)

        if test_data.get("bucket_filenames"):
            resources = test_data.get("bucket_filenames")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, dest_folder=directory.path
        )
        os.mkdir(os.path.join(directory.path, "preprint"))
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )

        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # do the activity
        result = self.activity.do_activity(self.activity_data)

        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in [
            "generate",
            "upload",
            "activity",
            "email",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value} in {comment}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                    comment=test_data.get("comment"),
                ),
            )
        # Count XML files in the output directory
        file_count = len(os.listdir(self.activity.directories.get("INPUT_DIR")))
        self.assertEqual(
            file_count, test_data.get("expected_file_count"), test_data.get("comment")
        )
        # Count XML files in output bucket
        preprint_bucket_folder = os.path.join(directory.path, "preprint")
        try:
            file_count = len(os.listdir(preprint_bucket_folder))
        except FileNotFoundError:
            file_count = 0
        self.assertEqual(
            file_count, test_data.get("expected_file_count"), test_data.get("comment")
        )

        # assert which XML files were uploaded to the bucket
        self.assertEqual(
            sorted(os.listdir(preprint_bucket_folder)),
            test_data.get("expected_bucket_files"),
        )

    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(activity_module, "storage_context")
    @patch("provider.preprint.download_original_preprint_xml")
    @patch.object(activity_module, "get_session")
    def test_preprint_xml_exception(
        self,
        fake_session,
        fake_download,
        fake_storage_context,
        fake_get_docmap,
    ):
        "test if an exception is raised downloading preprint XML from the bucket"
        directory = TempDirectory()
        fake_session.return_value = self.session

        resources = ["elife-preprint-92362-v1.xml"]

        # populate the bucket previous folder file paths and files
        next_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        resources += self.populate_docmap_index_files(directory.path, next_docmap_index)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_84364.json")
        fake_download.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch.object(cleaner, "get_docmap")
    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(activity_module, "get_session")
    def test_docmap_exception(
        self,
        fake_session,
        fake_download_storage_context,
        fake_storage_context,
        fake_get_docmap,
    ):
        "test if an exception is raised getting the docmap string"
        directory = TempDirectory()
        fake_session.return_value = self.session

        resources = ["elife-preprint-92362-v1.xml"]

        # populate the bucket previous folder file paths and files
        next_docmap_index = {"docmaps": []}
        resources += self.populate_docmap_index_files(directory.path, next_docmap_index)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_get_docmap.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch("provider.preprint.build_article")
    @patch.object(cleaner, "get_docmap")
    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "get_session")
    def test_build_article_exception(
        self,
        fake_session,
        fake_get_current_datetime,
        fake_download_storage_context,
        fake_storage_context,
        fake_get_docmap,
        fake_build_article,
    ):
        "test if an exception is raised building the article object"
        directory = TempDirectory()
        fake_session.return_value = self.session
        date_time = "2023-11-23 +0000"
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            date_time, "%Y-%m-%d %z"
        )

        resources = ["elife-preprint-92362-v1.xml"]

        # populate the bucket previous folder file paths and files
        next_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        resources += self.populate_docmap_index_files(directory.path, next_docmap_index)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")
        fake_build_article.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch("provider.preprint.preprint_xml")
    @patch("provider.preprint.build_article")
    @patch.object(cleaner, "get_docmap")
    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "get_session")
    def test_generate_preprint_xml_exception(
        self,
        fake_session,
        fake_get_current_datetime,
        fake_download_storage_context,
        fake_storage_context,
        fake_get_docmap,
        fake_build_article,
        fake_preprint_xml,
    ):
        "test if an exception is raised generating preprint XML"
        directory = TempDirectory()
        fake_session.return_value = self.session
        date_time = "2023-11-23 +0000"
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            date_time, "%Y-%m-%d %z"
        )

        resources = ["elife-preprint-92362-v1.xml"]

        # populate the bucket previous folder file paths and files
        next_docmap_index = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        resources += self.populate_docmap_index_files(directory.path, next_docmap_index)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")
        fake_build_article.return_value = True
        fake_preprint_xml.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)


class TestMissingSettings(unittest.TestCase):
    def setUp(self):
        self.epp_data_bucket = settings_mock.epp_data_bucket

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.epp_data_bucket = self.epp_data_bucket

    def test_missing_settings(self):
        "test if settings is missing a required value"
        settings_mock.epp_data_bucket = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, True)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "epp_data_bucket in settings is blank, skipping FindNewPreprints.",
        )


class TestDocmapDetailMap(unittest.TestCase):
    "tests for docmap_detail_map()"

    def setUp(self):
        date_time = "2023-11-23 +0000"
        self.current_datetime = datetime.datetime.strptime(date_time, "%Y-%m-%d %z")
        self.day_interval = 7

    def test_docmap_detail_map(self):
        "test returning matched preprint data"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        docmap_index_json = {"docmaps": [docmap_json]}
        expected = {
            "elife-preprint-87445-v2.xml": {"article_id": 87445, "version": "2"}
        }
        # invoke
        result = activity_module.docmap_detail_map(
            docmap_index_json, self.current_datetime, self.day_interval, settings_mock
        )
        # assert
        self.assertDictEqual(result, expected)

    def test_future_published_date(self):
        "test published date is in the future"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        # change the published value
        docmap_json["steps"]["_:b5"]["actions"][0]["outputs"][0][
            "published"
        ] = "2023-11-24T14:00:00+00:00"
        docmap_index_json = {"docmaps": [docmap_json]}
        expected = {}
        # invoke
        result = activity_module.docmap_detail_map(
            docmap_index_json, self.current_datetime, self.day_interval, settings_mock
        )
        # assert
        self.assertEqual(result, expected)

    def test_old_published_date(self):
        "test if no published date in the docmap"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        # change the published value
        docmap_json["steps"]["_:b5"]["actions"][0]["outputs"][0][
            "published"
        ] = "2023-11-01T14:00:00+00:00"
        docmap_index_json = {"docmaps": [docmap_json]}
        expected = {}
        # invoke
        result = activity_module.docmap_detail_map(
            docmap_index_json, self.current_datetime, self.day_interval, settings_mock
        )
        # assert
        self.assertEqual(result, expected)

    def test_not_published(self):
        "test if no published date in the docmap"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        # delete the published value
        del docmap_json["steps"]["_:b5"]["actions"][0]["outputs"][0]["published"]
        docmap_index_json = {"docmaps": [docmap_json]}
        expected = {}
        # invoke
        result = activity_module.docmap_detail_map(
            docmap_index_json, self.current_datetime, self.day_interval, settings_mock
        )
        # assert
        self.assertEqual(result, expected)
