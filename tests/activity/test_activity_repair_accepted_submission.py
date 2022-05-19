# coding=utf-8

import os
import glob
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_RepairAcceptedSubmission as activity_module
from activity.activity_RepairAcceptedSubmission import (
    activity_RepairAcceptedSubmission as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestRepairAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory, including the cleaner.log file
        helpers.delete_files_in_folder(self.activity.get_tmp_dir())

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_repair_xml_status": True,
            "expected_output_xml_status": True,
            "expected_upload_xml_status": True,
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

        zip_file_base = test_data.get("filename").rstrip(".zip")
        xml_file = "%s/%s.xml" % (zip_file_base, zip_file_base)

        fake_clean_tmp_dir.return_value = None

        # expanded bucket files
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            test_data.get("filename"),
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        temp_dir_files = glob.glob(self.activity.directories.get("INPUT_DIR") + "/*/*")

        xml_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"),
            zip_file_base,
            "%s.xml" % zip_file_base,
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            (
                "failed in {comment}, got {result}, filename {filename}, "
                + "input_file {input_file}"
            ).format(
                comment=test_data.get("comment"),
                result=result,
                input_file=self.activity.input_file,
                filename=filename_used,
            ),
        )

        self.assertEqual(
            self.activity.statuses.get("repair_xml"),
            test_data.get("expected_repair_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("output_xml"),
            test_data.get("expected_output_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # the new XML file should include the repaired XML namespace
        bucket_folder_path = os.path.join(
            dest_folder,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_base,
        )
        repaired_xml_file_path = os.path.join(
            bucket_folder_path, "%s.xml" % zip_file_base
        )
        with open(repaired_xml_file_path, "r", encoding="utf-8") as open_file:
            self.assertEqual(
                (
                    '<?xml version="1.0" ?><article article-type="research-article"'
                    ' xmlns:xlink="http://www.w3.org/1999/xlink">\n'
                ),
                open_file.readline(),
            )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "parse_article_xml")
    def test_do_activity_exception_parseerror(
        self,
        fake_parse_article_xml,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        zip_file_base = "30-01-2019-RA-eLife-45644"
        zip_file = "%s.zip" % zip_file_base
        xml_file = "%s/%s.xml" % (zip_file_base, zip_file_base)
        xml_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"),
            xml_file,
        )
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_file,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_parse_article_xml.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "RepairAcceptedSubmission, XML ParseError exception parsing XML %s for file %s"
            )
            % (xml_file_path, zip_file),
        )
