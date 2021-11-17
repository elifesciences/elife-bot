# coding=utf-8

import os
import unittest
from mock import patch
from provider import cleaner
import activity.activity_TransformAcceptedSubmission as activity_module
from activity.activity_TransformAcceptedSubmission import (
    activity_TransformAcceptedSubmission as activity_object,
)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.helpers as helpers
import tests.activity.test_activity_data as activity_test_data
import tests.test_data as test_case_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


class TestTransformAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean folder used by storage context
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity(self, fake_download_storage_context, fake_storage_context):
        test_data = {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_transform_status": True,
        }

        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_storage_context.return_value = FakeStorageContext()

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
            self.activity.statuses.get("transform"),
            test_data.get("expected_transform_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r") as open_file:
            log_contents = open_file.read()
        log_infos = [
            line
            for line in log_contents.split("\n")
            if "INFO elifecleaner:transform:" in line
        ]
        # check output bucket folder contents
        self.assertTrue(
            "30-01-2019-RA-eLife-45644.zip"
            in os.listdir(activity_test_data.ExpandArticle_files_dest_folder)
        )

        # compare some log file values,
        # these assertions can be removed if any are too hard to manage
        self.assertTrue(
            log_infos[0].endswith("30-01-2019-RA-eLife-45644.zip starting to transform")
        )
        self.assertTrue(
            log_infos[1].endswith(
                "30-01-2019-RA-eLife-45644.zip code_file_name: Figure 5source code 1.c"
            )
        )
        self.assertTrue(
            log_infos[2].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip from_file: "
                    'ArticleZipFile("Figure 5source code 1.c", '
                    '"30-01-2019-RA-eLife-45644/Figure 5source code 1.c", '
                    '"%s/30-01-2019-RA-eLife-45644/Figure 5source code 1.c")'
                )
                % self.activity.directories.get("TEMP_DIR")
            )
        )
        self.assertTrue(
            log_infos[3].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip to_file: "
                    'ArticleZipFile("Figure 5source code 1.c.zip", '
                    '"30-01-2019-RA-eLife-45644/Figure 5source code 1.c.zip", '
                    '"%s/Figure 5source code 1.c.zip")'
                )
                % self.activity.directories.get("OUTPUT_DIR")
            )
        )
        self.assertTrue(
            log_infos[4].endswith("30-01-2019-RA-eLife-45644.zip rewriting xml tags")
        )
        self.assertTrue(
            log_infos[5].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip writing xml to file "
                    "%s/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
                )
                % self.activity.directories.get("TEMP_DIR")
            )
        )
        self.assertTrue(
            log_infos[6].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip writing new zip file "
                    "%s/30-01-2019-RA-eLife-45644.zip"
                )
                % self.activity.directories.get("OUTPUT_DIR")
            )
        )

    @patch.object(cleaner, "transform_ejp_zip")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_exception_unknown(
        self, fake_download_storage_context, fake_transform_ejp_zip
    ):
        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()

        fake_transform_ejp_zip.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                (
                    "TransformAcceptedSubmission, unhandled exception in "
                    "cleaner.transform_ejp_zip for file %s/30-01-2019-RA-eLife-45644.zip"
                )
                % self.activity.directories.get("INPUT_DIR")
            ),
        )
