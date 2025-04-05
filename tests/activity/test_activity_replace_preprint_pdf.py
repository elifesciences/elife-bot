# coding=utf-8

import unittest
import os
import copy
from mock import patch
from testfixtures import TempDirectory
import activity.activity_ReplacePreprintPDF as activity_module
from activity.activity_ReplacePreprintPDF import (
    activity_ReplacePreprintPDF as activity_class,
)
from tests import list_files
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestReplacePreprintPdf(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_storage_context,
        fake_get,
    ):
        "test if there is a pdf_url in the session"
        directory = TempDirectory()

        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        session_dict = copy.copy(SESSION_DICT)
        session_dict["pdf_url"] = pdf_url
        fake_session.return_value = FakeSession(session_dict)

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        fake_response = FakeResponse(200)
        # a PDF file to test with
        pdf_fixture = "tests/files_source/elife-00353-v1.pdf"
        with open(pdf_fixture, "rb") as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertTrue(
            (
                "ReplacePreprintPDF, got pdf_href content/24301711.pdf from"
                " manifest.xml for 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ReplacePreprintPDF,"
                " downloading https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
                " to %s/content/24301711.pdf"
            )
            % self.activity.directories.get("INPUT_DIR")
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            "ReplacePreprintPDF, replacing pdf content/24301711.pdf in the bucket expanded folder"
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ReplacePreprintPDF statuses:"
                " {'pdf_url': True, 'pdf_href': True, 'download_pdf': True, 'replace_pdf': True}"
            )
            in self.activity.logger.loginfo,
        )

        # assertions on files
        self.assertEqual(
            list_files(self.activity.directories.get("INPUT_DIR")),
            ["content/24301711.pdf"],
        )

        # assertions on bucket contents
        bucket_expanded_folder_path = os.path.join(
            directory.path, session_dict.get("expanded_folder")
        )
        bucket_pdf_path = os.path.join(
            bucket_expanded_folder_path, "content/24301711.pdf"
        )
        self.assertTrue(
            os.path.exists(bucket_pdf_path),
            "PDF missing from the bucket expanded folder",
        )
        self.assertEqual(
            os.stat(bucket_pdf_path).st_size,
            os.stat(pdf_fixture).st_size,
            "bucket PDF file size did not match the PDF fixture",
        )

    @patch.object(activity_module, "get_session")
    def test_do_activity_no_pdf_url(
        self,
        fake_session,
    ):
        "test if no pdf_url is in the session"
        session_dict = copy.copy(SESSION_DICT)
        fake_session.return_value = FakeSession(session_dict)

        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        self.assertEqual(
            self.activity.logger.logerror,
            (
                "ReplacePreprintPDF, no pdf_url found in the session for"
                " 10.7554/eLife.95901.1, failing the workflow"
            ),
        )
