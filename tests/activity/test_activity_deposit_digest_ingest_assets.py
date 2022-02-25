# coding=utf-8

import os
import unittest
from mock import patch
from ddt import ddt, data
from provider import digest_provider, download_helper
from activity.activity_DepositDigestIngestAssets import (
    activity_DepositDigestIngestAssets as activity_object,
)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


def input_data(file_name_to_change=None):
    activity_data = test_case_data.ingest_digest_data
    if file_name_to_change is not None:
        activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestDepositDigestIngestAssets(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(download_helper, "storage_context")
    @patch.object(digest_provider, "storage_context")
    @patch("activity.activity_DepositDigestIngestAssets.storage_context")
    @data(
        {
            "comment": "digest docx file example",
            "filename": "DIGEST+99999.docx",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": "https://doi.org/10.7554/eLife.99999",
            "expected_digest_image_file": None,
            "expected_dest_resource": None,
            "expected_file_list": [],
        },
        {
            "comment": "digest zip file example",
            "filename": "DIGEST+99999.zip",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_digest_doi": "https://doi.org/10.7554/eLife.99999",
            "expected_digest_image_file": "IMAGE 99999.jpeg",
            "expected_dest_resource": "s3://ppd_cdn_bucket/digests/99999/digest-99999.jpeg",
            "expected_file_list": ["digest-99999.jpeg"],
        },
        {
            "comment": "digest file does not exist example",
            "filename": "",
            "expected_digest_doi": None,
            "expected_digest_image_file": None,
            "expected_dest_resource": None,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_file_list": [],
        },
        {
            "comment": "bad digest docx file example",
            "filename": "DIGEST+99998.docx",
            "expected_digest_doi": None,
            "expected_digest_image_file": None,
            "expected_dest_resource": None,
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
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
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
        # check digest values
        digest_doi = None
        if self.activity.digest:
            digest_doi = self.activity.digest.doi
        self.assertEqual(
            digest_doi,
            test_data.get("expected_digest_doi"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # check digest image values
        digest_image_file = None
        if (
            self.activity.digest
            and self.activity.digest.image
            and self.activity.digest.image.file
        ):
            digest_image_file = self.activity.digest.image.file.split(os.sep)[-1]
        self.assertEqual(
            digest_image_file,
            test_data.get("expected_digest_image_file"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # Check the S3 object destination resource
        self.assertEqual(
            self.activity.dest_resource,
            test_data.get("expected_dest_resource"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # Check destination folder as a list
        files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(
            compare_files,
            test_data.get("expected_file_list"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )


if __name__ == "__main__":
    unittest.main()
