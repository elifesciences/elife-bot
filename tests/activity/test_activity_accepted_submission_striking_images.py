# coding=utf-8

import copy
import os
import glob
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_AcceptedSubmissionStrikingImages as activity_module
from activity.activity_AcceptedSubmissionStrikingImages import (
    activity_AcceptedSubmissionStrikingImages as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestAcceptedSubmissionStrikingImages(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(
            copy.copy(test_activity_data.accepted_session_example)
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no cover art",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "expected_result": True,
            "expected_images_status": None,
            "expected_upload_xml_status": None,
            "expected_rename_files_status": None,
            "expected_upload_files_status": None,
        },
        {
            "comment": "example with cover art",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_images_status": True,
            "expected_upload_xml_status": True,
            "expected_rename_files_status": True,
            "expected_upload_files_status": True,
            "expected_xml_contains": [
                ("<upload_file_nm>45644-a_striking_image.tif</upload_file_nm>"),
            ],
            "expected_bucket_upload_folder_contents": [
                "30-01-2019-RA-eLife-45644.xml",
                "45644-a_striking_image.tif",
            ],
            "expected_striking_images_bucket_folder_contents": [
                "45644-a_striking_image.tif"
            ],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        zip_sub_folder = test_data.get("filename").replace(".zip", "")
        zip_xml_file = "%s.xml" % zip_sub_folder
        article_id = zip_sub_folder.rsplit("-", 1)[1]

        zip_file_path = os.path.join("tests", "files_source", test_data.get("filename"))

        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, test_data.get("expected_result"))

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            zip_sub_folder,
            zip_xml_file,
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        # assertion on XML contents
        if test_data.get("expected_xml_contains"):
            with open(xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains"):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        for status_type in ["images", "upload_xml", "rename_files", "upload_files"]:
            self.assertEqual(
                self.activity.statuses.get(status_type),
                test_data.get("expected_%s_status" % status_type),
                "status_type {status_type} failed in {comment}".format(
                    status_type=status_type, comment=test_data.get("comment")
                ),
            )

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on cleaner.log contents
        if test_data.get("expected_cleaner_log_contains"):
            log_file_path = os.path.join(
                self.activity.get_tmp_dir(), self.activity.activity_log_file
            )
            with open(log_file_path, "r", encoding="utf8") as open_file:
                log_contents = open_file.read()
            for fragment in test_data.get("expected_cleaner_log_contains"):
                self.assertTrue(
                    fragment in log_contents,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on the session cleaner log content
        if test_data.get("expected_upload_xml_status"):
            session_log = self.session.get_value("cleaner_log")
            self.assertIsNotNone(
                session_log,
                "failed in {comment}".format(comment=test_data.get("comment")),
            )

        # check output bucket folder contents
        if "expected_bucket_upload_folder_contents" in test_data:
            bucket_folder_path = os.path.join(
                directory.path,
                test_activity_data.accepted_session_example.get("expanded_folder"),
                zip_sub_folder,
            )
            try:
                output_bucket_list = os.listdir(bucket_folder_path)
            except FileNotFoundError:
                # no objects were uploaded so the folder path does not exist
                output_bucket_list = []
            for bucket_file in test_data.get("expected_bucket_upload_folder_contents"):
                self.assertTrue(
                    bucket_file in output_bucket_list,
                    "%s not found in bucket upload folder" % bucket_file,
                )

        # check striking images bucket folder contents
        if "expected_striking_images_bucket_folder_contents" in test_data:
            bucket_folder_path = os.path.join(directory.path, article_id, "vor")
            try:
                output_bucket_list = os.listdir(bucket_folder_path)
            except FileNotFoundError:
                # no objects were uploaded so the folder path does not exist
                output_bucket_list = []
            for bucket_file in test_data.get(
                "expected_striking_images_bucket_folder_contents"
            ):
                self.assertTrue(
                    bucket_file in output_bucket_list,
                    "%s not found in striking images bucket folder" % bucket_file,
                )
