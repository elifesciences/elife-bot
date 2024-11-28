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
import activity.activity_AcceptedSubmissionPeerReviewTables as activity_module
from activity.activity_AcceptedSubmissionPeerReviewTables import (
    activity_AcceptedSubmissionPeerReviewTables as activity_object,
)
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
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
class TestAcceptedSubmissionPeerReviewTables(unittest.TestCase):
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

    def add_sub_article_xml(self, filename, directory, sub_article_xml):
        "add XML to the XML file"
        xml_filename = "%s.xml" % filename.rsplit(".", 1)[0]
        xml_path = helpers.expanded_article_xml_path(
            xml_filename,
            directory.path,
            self.session.get_value("expanded_folder"),
        )
        helpers.add_sub_article_xml(
            xml_path,
            sub_article_xml,
        )

    def copy_files(self, image_names):
        "copy image files into the folder for testing"
        file_details = []
        for image_name in image_names:
            details = {
                "file_path": "tests/files_source/digests/outbox/99999/digest-99999.jpg",
                "file_type": "figure",
                "upload_file_nm": image_name,
            }
            file_details.append(details)
        return file_details

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "image_names": None,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewTables, no inline-graphic tags in "
                    "30-01-2019-RA-eLife-45644.zip"
                )
            ],
        },
        {
            "comment": "example with no label or caption content inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                '<p><inline-graphic xlink:href="local.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": ["local.jpg"],
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_xml_contains": [
                (
                    '<sub-article id="sa1">'
                    "<body>"
                    '<p><inline-graphic xlink:href="local.jpg"/></p>'
                    "</body>"
                    "</sub-article>"
                ),
            ],
        },
        {
            "comment": "example with label and caption",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph.</p>"
                "<p><bold>Review table 1.</bold></p>"
                "<p>Caption title. Caption paragraph.</p>"
                '<p><inline-graphic xlink:href="elife-45644-inf1.jpg"/></p>'
                "</body>"
                "</sub-article>"
                '<sub-article id="sa2">'
                "<body>"
                "<p>First paragraph.</p>"
                "<p><bold>Review table 1.</bold></p>"
                "<p>Caption title. Caption paragraph.</p>"
                '<p><inline-graphic xlink:href="local2.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": ["elife-45644-inf1.jpg", "local2.jpg"],
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_xml_contains": [
                (
                    '<sub-article id="sa1">'
                    "<body>"
                    "<p>First paragraph.</p>"
                    '<table-wrap id="sa1table1">'
                    "<label>Review table 1.</label>"
                    "<caption>"
                    "<title>Caption title.</title>"
                    "<p>Caption paragraph.</p>"
                    "</caption>"
                    '<graphic mimetype="image" mime-subtype="jpg"'
                    ' xlink:href="elife-45644-sa1-table1.jpg"/>'
                    "</table-wrap>"
                    "</body>"
                    "</sub-article>"
                    '<sub-article id="sa2">'
                    "<body>"
                    "<p>First paragraph.</p>"
                    '<table-wrap id="sa2table1">'
                    "<label>Review table 1.</label>"
                    "<caption>"
                    "<title>Caption title.</title>"
                    "<p>Caption paragraph.</p>"
                    "</caption>"
                    '<graphic mimetype="image" mime-subtype="jpg" xlink:href="sa2-table1.jpg"/>'
                    "</table-wrap>"
                    "</body>"
                    "</sub-article>"
                    "</article>"
                ),
            ],
            "expected_bucket_upload_folder_contents": [
                "30-01-2019-RA-eLife-45644.xml",
                "elife-45644-sa1-table1.jpg",
                "sa2-table1.jpg",
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

        # create a new zip file fixture
        file_details = []
        if test_data.get("image_names"):
            file_details = self.copy_files(test_data.get("image_names"))
        new_zip_file_path = helpers.add_files_to_accepted_zip(
            "tests/files_source/30-01-2019-RA-eLife-45644.zip",
            directory.path,
            file_details,
        )

        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            new_zip_file_path,
        )

        # write additional XML to the XML file
        if test_data.get("sub_article_xml"):
            self.add_sub_article_xml(
                test_data.get("filename"), directory, test_data.get("sub_article_xml")
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

        self.assertEqual(
            self.activity.statuses.get("hrefs"),
            test_data.get("expected_hrefs_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
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

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_object, "copy_expanded_folder_files")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @data(
        {
            "comment": "example with no label or caption content inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph.</p>"
                "<p><bold>Review table 1.</bold></p>"
                "<p>Caption title. Caption paragraph.</p>"
                '<p><inline-graphic xlink:href="local.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": ["local.jpg"],
            "expected_result": True,
        },
    )
    def test_do_activity_copy_files_exception(
        self,
        test_data,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_copy_files,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()

        # create a new zip file fixtur
        file_details = []
        if test_data.get("image_names"):
            file_details = self.copy_files(test_data.get("image_names"))
        new_zip_file_path = helpers.add_files_to_accepted_zip(
            "tests/files_source/30-01-2019-RA-eLife-45644.zip",
            directory.path,
            file_details,
        )

        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            new_zip_file_path,
        )

        # write additional XML to the XML file
        if test_data.get("sub_article_xml"):
            self.add_sub_article_xml(
                test_data.get("filename"), directory, test_data.get("sub_article_xml")
            )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session
        fake_copy_files.side_effect = RuntimeError("An exception")
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, test_data.get("expected_result"))

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_object, "rename_expanded_folder_files")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @data(
        {
            "comment": "example with no label or caption content inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph.</p>"
                "<p><bold>Review table 1.</bold></p>"
                "<p>Caption title. Caption paragraph.</p>"
                '<p><inline-graphic xlink:href="local.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": ["local.jpg"],
            "expected_result": True,
        },
    )
    def test_do_activity_rename_files_exception(
        self,
        test_data,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_rename_files,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()

        # create a new zip file fixtur
        file_details = []
        if test_data.get("image_names"):
            file_details = self.copy_files(test_data.get("image_names"))
        new_zip_file_path = helpers.add_files_to_accepted_zip(
            "tests/files_source/30-01-2019-RA-eLife-45644.zip",
            directory.path,
            file_details,
        )

        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            new_zip_file_path,
        )

        # write additional XML to the XML file
        if test_data.get("sub_article_xml"):
            self.add_sub_article_xml(
                test_data.get("filename"), directory, test_data.get("sub_article_xml")
            )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session
        fake_rename_files.side_effect = RuntimeError("An exception")
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, test_data.get("expected_result"))
