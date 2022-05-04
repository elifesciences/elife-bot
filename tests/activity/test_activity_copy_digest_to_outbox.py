# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
from testfixtures import TempDirectory
from provider import digest_provider, download_helper
from activity.activity_CopyDigestToOutbox import (
    activity_CopyDigestToOutbox as activity_object,
)
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.test_data as test_case_data


def input_data(file_name_to_change=None):
    activity_data = test_case_data.ingest_digest_data
    if file_name_to_change is not None:
        activity_data["file_name"] = file_name_to_change
    return activity_data


def populate_outbox(resources, to_dir):
    "populate the bucket with outbox files to later be deleted"
    for resource in resources:
        file_name = resource.split("/")[-1]
        file_path = to_dir + "/" + file_name
        with open(file_path, "a"):
            os.utime(file_path, None)


@ddt
class TestCopyDigestToOutbox(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(download_helper, "storage_context")
    @patch.object(digest_provider, "storage_context")
    @patch("activity.activity_CopyDigestToOutbox.storage_context")
    @data(
        {
            "comment": "digest docx file example",
            "filename": "DIGEST+99999.docx",
            "msid": "99999",
            "bucket_resources": ["DIGEST 99999_alternate.docx"],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_file_list": ["digest-99999.docx"],
        },
        {
            "comment": "digest zip file example",
            "filename": "DIGEST+99999.zip",
            "msid": "99999",
            "bucket_resources": [
                "IMAGE 99999.jpg",
                "DIGEST 99999_old.docx",
            ],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_file_list": ["digest-99999.docx", "digest-99999.jpeg"],
        },
        {
            "comment": "digest file does not exist example",
            "filename": "",
            "msid": "99999",
            "bucket_resources": [],
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": [],
        },
        {
            "comment": "bad digest docx file example",
            "filename": "DIGEST+99998.docx",
            "msid": "99998",
            "bucket_resources": [],
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": [],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_storage_context,
        fake_provider_storage_context,
        fake_download_storage_context,
    ):
        directory = TempDirectory()
        # copy files into the input directory using the storage context
        populate_outbox(test_data.get("bucket_resources"), directory.path)
        dest_folder = os.path.join(directory.path, "files_dest")
        os.mkdir(dest_folder)
        activity_storage_context = FakeStorageContext(
            directory.path, test_data.get("bucket_resources"), dest_folder=dest_folder
        )
        fake_storage_context.return_value = activity_storage_context
        fake_provider_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # Check destination folder as a list
        outbox_folder_path = os.path.join(
            dest_folder, "digests", "outbox", test_data.get("msid")
        )
        if os.path.exists(outbox_folder_path):
            files = sorted(os.listdir(outbox_folder_path))
        else:
            files = []
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(
            compare_files,
            test_data.get("expected_file_list"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        TempDirectory.cleanup_all()


if __name__ == "__main__":
    unittest.main()
