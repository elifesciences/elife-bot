# coding=utf-8

import os
import unittest
import shutil
import zipfile
from mock import patch
from testfixtures import TempDirectory
import activity.activity_OutputMeca as activity_module
from activity.activity_OutputMeca import (
    activity_OutputMeca as activity_class,
)
from tests import list_files
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import settings_mock, test_activity_data


class TestOutputMeca(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(self, fake_storage_context, fake_session):
        directory = TempDirectory()
        # expand input meca file zip into the bucket expanded folder
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        dest_folder = os.path.join(
            directory.path,
            test_activity_data.ingest_meca_session_example().get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(dest_folder, exist_ok=True)
        with zipfile.ZipFile(meca_file_path, "r") as open_zipfile:
            resources = open_zipfile.namelist()
            open_zipfile.extractall(dest_folder)

        fake_storage_context.return_value = FakeStorageContext(
            dest_folder, resources, dest_folder=directory.path
        )

        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )

        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_download_status = True

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)

        # check assertions
        self.assertEqual(
            result,
            expected_result,
        )

        self.assertEqual(
            self.activity.statuses.get("download"),
            expected_download_status,
        )

        # check the contents of the zip file
        zip_file_path = os.path.join(
            directory.path,
            "reviewed-preprints",
            "95901-v1-meca.zip",
        )
        with zipfile.ZipFile(zip_file_path, "r") as open_zipfile:
            resources = open_zipfile.namelist()
        self.assertEqual(len(resources), 12)

        files = list_files(dest_folder)

        self.assertEqual(sorted(resources), sorted(files))


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.meca_bucket = settings_mock.meca_bucket

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_bucket = self.meca_bucket

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.meca_bucket
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "OutputMeca, meca_bucket in settings is missing, skipping",
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.meca_bucket = settings_mock.meca_bucket

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.meca_bucket = self.meca_bucket

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.meca_bucket = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            "OutputMeca, meca_bucket in settings is blank, skipping",
        )
