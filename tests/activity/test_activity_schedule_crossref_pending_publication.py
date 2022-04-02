# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_ScheduleCrossrefPendingPublication as activity_module
from activity.activity_ScheduleCrossrefPendingPublication import (
    activity_ScheduleCrossrefPendingPublication as activity_object,
)
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
import tests.test_data as test_case_data
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestScheduleCrossrefPendingPublication(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(
            test_activity_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("provider.outbox_provider.storage_context")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_session,
        fake_cleaner_storage_context,
        fake_outbox_storage_context,
    ):
        directory = TempDirectory()
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

        # copy files into the input directory using the storage context
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources=resources
        )
        fake_outbox_storage_context.return_value = FakeStorageContext()
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
