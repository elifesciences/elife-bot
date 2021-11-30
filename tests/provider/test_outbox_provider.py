import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import outbox_provider
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.helpers as helpers
import tests.activity.test_activity_data as activity_test_data


class TestOutboxProvider(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.good_xml_file = "tests/test_data/crossref/outbox/elife-18753-v1.xml"
        self.bad_xml_file = "tests/test_data/activity.json"

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    def test_get_to_folder_name(self):
        folder_name = ""
        date_stamp = ""
        expected = folder_name + date_stamp + "/"
        self.assertEqual(
            outbox_provider.get_to_folder_name(folder_name, date_stamp), expected
        )

    @patch("provider.outbox_provider.storage_context")
    def test_get_outbox_s3_key_names(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext(
            "tests/test_data/crossref/outbox/"
        )
        outbox_folder = "crossref/outbox/"
        expected = [outbox_folder.rstrip("/") + "/" + "elife-00353-v1.xml"]
        key_names = outbox_provider.get_outbox_s3_key_names(
            settings_mock, "", outbox_folder
        )
        # returns the default file name from FakeStorageContext in the test scenario
        self.assertEqual(key_names, expected)

    @patch("provider.outbox_provider.storage_context")
    def test_download_files_from_s3_outbox(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        bucket_name = ""
        outbox_folder = ""
        key_names = outbox_provider.get_outbox_s3_key_names(
            settings_mock, bucket_name, outbox_folder
        )
        result = outbox_provider.download_files_from_s3_outbox(
            settings_mock, bucket_name, key_names, self.directory.path, FakeLogger()
        )
        self.assertTrue(result)

    @patch.object(FakeStorageContext, "get_resource_to_file")
    @patch("provider.outbox_provider.storage_context")
    def test_download_files_from_s3_outbox_failure(
        self, fake_storage_context, fake_get_resource
    ):
        """test IOError exception for coverage"""
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_resource.side_effect = IOError
        bucket_name = ""
        outbox_folder = ""
        key_names = outbox_provider.get_outbox_s3_key_names(
            settings_mock, bucket_name, outbox_folder
        )
        result = outbox_provider.download_files_from_s3_outbox(
            settings_mock, bucket_name, key_names, self.directory.path, FakeLogger()
        )
        self.assertFalse(result)

    @patch("provider.outbox_provider.storage_context")
    def test_clean_outbox(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext(self.directory)
        # copy two files in for cleaning
        shutil.copy(self.good_xml_file, self.directory.path)
        shutil.copy(self.bad_xml_file, self.directory.path)
        # add outbox_folder name and one file to the list of published file names
        bucket_name = "bucket"
        outbox_folder = "crossref/outbox/"
        to_folder = "crossref/published/"
        published_file_names = [outbox_folder, self.good_xml_file]
        # clean outbox
        outbox_provider.clean_outbox(
            settings_mock, bucket_name, outbox_folder, to_folder, published_file_names
        )
        # TempDirectory should have one file remaining
        self.assertTrue(len(os.listdir(self.directory.path)), 1)

    @patch("provider.outbox_provider.storage_context")
    def test_upload_files_to_s3_folder(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        file_names = [self.good_xml_file]
        expected = [file_name.split(os.sep)[-1] for file_name in file_names]
        outbox_provider.upload_files_to_s3_folder(
            settings_mock, "bucket", "to_folder/", file_names
        )
        # filter out the .gitkeep file before comparing
        uploaded_files = [
            file_name
            for file_name in os.listdir(
                activity_test_data.ExpandArticle_files_dest_folder
            )
            if file_name.endswith(".xml")
        ]
        self.assertEqual(uploaded_files, expected)


class TestGetOutboxFolder(unittest.TestCase):
    def test_outbox_folder(self):
        for workflow in outbox_provider.DOWNSTREAM_WORKFLOW_MAP:
            foldername = outbox_provider.workflow_foldername(workflow)
            self.assertIsNotNone(outbox_provider.outbox_folder(foldername))

    def test_outbox_folder_undefined(self):
        foldername = "foo"
        self.assertIsNone(outbox_provider.outbox_folder(foldername))


class TestGetPublishedFolder(unittest.TestCase):
    def test_published_folder(self):
        for workflow in outbox_provider.DOWNSTREAM_WORKFLOW_MAP:
            foldername = outbox_provider.workflow_foldername(workflow)
            self.assertIsNotNone(outbox_provider.published_folder(foldername))

    def test_published_folder_undefined(self):
        foldername = "foo"
        self.assertIsNone(outbox_provider.published_folder(foldername))


class TestGetNotPublishedFolder(unittest.TestCase):
    def test_not_published_folder(self):
        for workflow in outbox_provider.DOWNSTREAM_WORKFLOW_MAP:
            foldername = outbox_provider.workflow_foldername(workflow)
            self.assertIsNotNone(outbox_provider.not_published_folder(foldername))

    def test_not_published_folder_undefined(self):
        foldername = "foo"
        self.assertIsNone(outbox_provider.not_published_folder(foldername))
