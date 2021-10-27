# coding=utf-8

import unittest
from xml.parsers.expat import ExpatError
from mock import patch
from ddt import ddt, data
from elifetools import xmlio
import activity.activity_ScheduleCrossrefPendingPublication as activity_module
from activity.activity_ScheduleCrossrefPendingPublication import (
    activity_ScheduleCrossrefPendingPublication as activity_object,
)
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.test_data as test_case_data
from tests.activity import helpers, settings_mock
import tests.activity.test_activity_data as testdata


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
        # clean the temporary directory
        self.activity.clean_tmp_dir()
        # clean out the bucket destination folder
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
        },
    )
    def test_do_activity(
        self, test_data, fake_download_storage_context, fake_storage_context
    ):
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

    @patch.object(xmlio, "output_root")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity_exception_parseerror(
        self, fake_download_storage_context, fake_output_root
    ):
        # copy files into the input directory using the storage context
        fake_download_storage_context.return_value = FakeStorageContext()

        fake_output_root.side_effect = ExpatError()
        # do the activity
        result = self.activity.do_activity(input_data("30-01-2019-RA-eLife-45644.zip"))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                (
                    "ScheduleCrossrefPendingPublication, XML ExpatError exception"
                    " in xmlio.output_root for file"
                )
            )
        )
