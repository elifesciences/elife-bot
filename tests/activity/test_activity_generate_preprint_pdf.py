# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import meca
import activity.activity_GeneratePreprintPDF as activity_module
from activity.activity_GeneratePreprintPDF import (
    activity_GeneratePreprintPDF as activity_class,
)
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestGeneratePreprintPdf(unittest.TestCase):
    "tests for do_activity()"

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch("requests.post")
    def test_do_activity(
        self,
        fake_post,
        fake_session,
        fake_storage_context,
        fake_outbox_storage_context,
    ):
        "test do_activity() returning a successful result"
        directory = TempDirectory()

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
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

        # mock outbox_provider storage
        temporary_s3_folder = "_sample_preprint_pdf"
        os.makedirs(os.path.join(directory.path, temporary_s3_folder))
        fake_outbox_storage_context.return_value = FakeStorageContext(directory.path)

        fake_session.return_value = FakeSession(SESSION_DICT)

        fake_post.return_value = FakeResponse(
            200,
            content=b"pdf",
        )

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertTrue(
            "GeneratePreprintPDF, endpoint url https://api/generate_preprint_pdf/"
            in self.activity.logger.loginfo,
        )
        temp = (
            "GeneratePreprintPDF, request to endpoint: POST data from file"
            " %s/content/24301711.xml"
        ) % (self.activity.directories.get("INPUT_DIR"))
        self.assertTrue(
            (
                "GeneratePreprintPDF, request to endpoint: POST data from file"
                " %s/content/24301711.xml to https://api/generate_preprint_pdf/"
            )
            % (self.activity.directories.get("INPUT_DIR"))
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "GeneratePreprintPDF, for article_id 95901 version 1 pdf_file_name:"
                " elife-preprint-95901-v1.pdf"
            )
            in self.activity.logger.loginfo,
        )

        # test temporary S3 folder
        s3_folder_contents = os.listdir(
            os.path.join(self.activity.directories.get("TEMP_DIR", temporary_s3_folder))
        )
        self.assertEqual(s3_folder_contents, ["elife-preprint-95901-v1.pdf"])

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_to_preprint_pdf_endpoint")
    def test_do_activity_endpoint_exception(
        self,
        fake_post_to_endpoint,
        fake_session,
        fake_storage_context,
    ):
        "test if an exception is raised when generating pdf_url from the endpoint"
        directory = TempDirectory()

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
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

        exception_message = "An exception"
        fake_post_to_endpoint.side_effect = RuntimeError(exception_message)

        fake_session.return_value = FakeSession(SESSION_DICT)
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintPDF, exception raised posting"
                " to endpoint https://api/generate_preprint_pdf/: %s"
            )
            % exception_message,
        )


class TestSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.generate_preprint_pdf_api_endpoint = (
            settings_mock.generate_preprint_pdf_api_endpoint
        )

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.generate_preprint_pdf_api_endpoint = (
            self.generate_preprint_pdf_api_endpoint
        )

    @patch.object(activity_module, "get_session")
    def test_missing_settings(self, fake_session):
        "test if settings is missing a required value"
        fake_session.return_value = FakeSession(SESSION_DICT)
        del settings_mock.generate_preprint_pdf_api_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "GeneratePreprintPDF, generate_preprint_pdf_api_endpoint"
                " in settings is missing, skipping"
            ),
        )

    @patch.object(activity_module, "get_session")
    def test_blank_settings(self, fake_session):
        "test if required settings value is blank"
        fake_session.return_value = FakeSession(SESSION_DICT)
        settings_mock.generate_preprint_pdf_api_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "GeneratePreprintPDF, generate_preprint_pdf_api_endpoint"
                " in settings is blank, skipping"
            ),
        )
