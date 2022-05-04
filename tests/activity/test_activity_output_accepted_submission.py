# coding=utf-8

import os
import unittest
import zipfile
from mock import patch
from testfixtures import TempDirectory
from provider import cleaner
import activity.activity_OutputAcceptedSubmission as activity_module
from activity.activity_OutputAcceptedSubmission import (
    activity_OutputAcceptedSubmission as activity_object,
)
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data
import tests.test_data as test_case_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


class TestOutputAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory, including the cleaner.log file
        helpers.delete_files_in_folder(self.activity.get_tmp_dir())

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self, fake_storage_context, fake_cleaner_storage_context, fake_session
    ):
        test_data = {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_download_status": True,
        }
        directory = TempDirectory()
        # copy files into the input directory using the storage context
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
        os.mkdir(dest_folder)
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")

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
            self.activity.statuses.get("download"),
            test_data.get("expected_download_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # check output bucket folder contents
        output_bucket_list = [
            file_name
            for file_name in os.listdir(dest_folder)
            if file_name != ".gitkeep"
        ]
        self.assertEqual(
            sorted(output_bucket_list),
            [test_data.get("filename")],
        )
        # check the contents of the zip file
        zip_file_path = os.path.join(
            dest_folder,
            test_data.get("filename"),
        )
        with zipfile.ZipFile(zip_file_path, "r") as open_zipfile:
            resources = open_zipfile.namelist()
        self.assertEqual(len(resources), 42)
        self.assertEqual(
            sorted(resources),
            [
                "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.pdf",
                "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
                "30-01-2019-RA-eLife-45644/Answers for the eLife digest.docx",
                "30-01-2019-RA-eLife-45644/Appendix 1.docx",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 1.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 12.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 13.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 14.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 15.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 2.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 3.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 4.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 5.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 6.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 7.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 8.png",
                "30-01-2019-RA-eLife-45644/Appendix 1figure 9.png",
                "30-01-2019-RA-eLife-45644/Figure 1.tif",
                "30-01-2019-RA-eLife-45644/Figure 2.tif",
                "30-01-2019-RA-eLife-45644/Figure 3.png",
                "30-01-2019-RA-eLife-45644/Figure 4.svg",
                "30-01-2019-RA-eLife-45644/Figure 4source data 1.zip",
                "30-01-2019-RA-eLife-45644/Figure 5.png",
                "30-01-2019-RA-eLife-45644/Figure 5source code 1.c",
                "30-01-2019-RA-eLife-45644/Figure 6.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 10_HorC.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 1_U crassus.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 2_U pictorum.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 3_M margaritifera.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 4_P auricularius.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 5_PesB.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 6_HavA.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 7_HavB.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 8_HavC.png",
                "30-01-2019-RA-eLife-45644/Figure 6figure supplement 9_HorB.png",
                "30-01-2019-RA-eLife-45644/Figure 6source data 1.pdf",
                "30-01-2019-RA-eLife-45644/Manuscript.docx",
                "30-01-2019-RA-eLife-45644/Potential striking image.tif",
                "30-01-2019-RA-eLife-45644/Table 2source data 1.xlsx",
                "30-01-2019-RA-eLife-45644/transparent_reporting_Sakalauskaite.docx",
            ],
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "download_asset_files_from_bucket")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_download_exception(
        self,
        fake_storage_context,
        fake_download,
        fake_cleaner_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True

        zip_filename = "30-01-2019-RA-eLife-45644.zip"
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_filename,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )

        fake_download.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(input_data(zip_filename))
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                (
                    "OutputAcceptedSubmission, exception in "
                    "download_all_files_from_bucket for file %s"
                )
                % zip_filename
            ),
        )
