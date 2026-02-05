# coding=utf-8

import os
import unittest
import shutil
import zipfile
from mock import patch
from testfixtures import TempDirectory
from provider import preprint
import activity.activity_OutputMeca as activity_module
from activity.activity_OutputMeca import (
    activity_OutputMeca as activity_class,
)
from tests import list_files
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data


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
    @patch.object(activity_class, "clean_tmp_dir")
    def test_do_activity(self, fake_clean_tmp_dir, fake_storage_context, fake_session):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        # expand input meca file zip into the bucket expanded folder
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            test_activity_data.ingest_meca_session_example().get("expanded_folder"),
        )

        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
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
            output_zip_namelist = open_zipfile.namelist()
        self.assertEqual(len(output_zip_namelist), 12)
        self.assertEqual(sorted(zip_file_paths), sorted(output_zip_namelist))

        article_xml_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"), "content", "24301711.xml"
        )
        self.assertTrue(
            ("OutputMeca, modifying XML namespaces in %s" % article_xml_path)
            in self.activity.logger.loginfo
        )

        with open(article_xml_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        self.assertTrue(
            (
                '<article xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xmlns:ali="http://www.niso.org/schemas/ali/1.0/"'
                ' xmlns:mml="http://www.w3.org/1998/Math/MathML"'
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' article-type="research-article" dtd-version="1.3" xml:lang="en">'
            )
            in xml_content
        )

    @patch.object(preprint, "modify_xml_namespaces")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_xml_namespaces_exception(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_session,
        fake_modify_xml_namespaces,
    ):
        "test if modifying XML namespaces raises an exception"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        # expand input meca file zip into the bucket expanded folder
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            test_activity_data.ingest_meca_session_example().get("expanded_folder"),
        )

        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )

        fake_modify_xml_namespaces.side_effect = Exception("An exception")

        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_download_status = True

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)

        # check assertions
        self.assertEqual(
            result,
            expected_result,
        )

        article_xml_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"), "content", "24301711.xml"
        )

        self.assertTrue(
            ("OutputMeca, modifying XML namespaces in %s" % article_xml_path)
            in self.activity.logger.loginfo
        )

        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception raised in modify_xml_namespaces for file %s:"
                " An exception"
            )
            % (
                self.activity.name,
                article_xml_path,
            ),
        )


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
