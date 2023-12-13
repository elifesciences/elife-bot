import os
import unittest
from mock import patch
from ddt import ddt, data
from testfixtures import TempDirectory
from provider import bigquery, cleaner
import activity.activity_FindNewPreprints as activity_module
from activity.activity_FindNewPreprints import (
    activity_FindNewPreprints as activity_class,
)
from tests import bigquery_preprint_test_data, read_fixture
from tests.classes_mock import (
    FakeSMTPServer,
    FakeBigQueryClient,
    FakeBigQueryRowIterator,
)
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
from tests.activity import settings_mock


@ddt
class TestFindNewPreprints(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()
        self.activity_data = {}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch.object(cleaner, "get_docmap")
    @patch.object(bigquery, "get_client")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.download_helper.storage_context")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch("requests.get")
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
        fake_get,
        fake_storage_context,
        fake_outbox_storage_context,
        fake_download_storage_context,
        fake_email_smtp_connect,
        fake_get_client,
        fake_get_docmap,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_84364.json")
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        resources = []
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
            "tests/files_source/epp", ["87445-v2.xml"]
        )

        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")

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
        file_count = len(os.listdir(self.activity.directories.get("OUTPUT_DIR")))
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

    @patch.object(bigquery, "get_client")
    def test_bigquery_exception(
        self,
        fake_get_client,
    ):
        "test if an exception is raised interacting with BigQuery"
        fake_get_client.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch.object(bigquery, "get_client")
    @patch.object(activity_module, "storage_context")
    @patch("provider.preprint.download_original_preprint_xml")
    def test_preprint_xml_exception(
        self,
        fake_download,
        fake_storage_context,
        fake_get_client,
    ):
        "test if an exception is raised downloading preprint XML from the bucket"
        directory = TempDirectory()
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        resources = ["elife-preprint-92362-v1.xml"]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch.object(cleaner, "get_docmap")
    @patch.object(bigquery, "get_client")
    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    def test_docmap_exception(
        self,
        fake_download_storage_context,
        fake_storage_context,
        fake_get_client,
        fake_get_docmap,
    ):
        "test if an exception is raised getting the docmap string"
        directory = TempDirectory()
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        resources = ["elife-preprint-92362-v1.xml"]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["87445-v2.xml"]
        )
        fake_get_docmap.side_effect = Exception("")

        result = self.activity.do_activity(self.activity_data)
        self.assertEqual(result, True)

    @patch("provider.preprint.build_article")
    @patch.object(cleaner, "get_docmap")
    @patch.object(bigquery, "get_client")
    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    def test_build_article_exception(
        self,
        fake_download_storage_context,
        fake_storage_context,
        fake_get_client,
        fake_get_docmap,
        fake_build_article,
    ):
        "test if an exception is raised building the article object"
        directory = TempDirectory()
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        resources = ["elife-preprint-92362-v1.xml"]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["87445-v2.xml"]
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")
        fake_build_article.side_effect = Exception("")

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
