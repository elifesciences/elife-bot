# coding=utf-8

import os
import copy
import json
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider, meca
import activity.activity_GeneratePreprintPDF as activity_module
from activity.activity_GeneratePreprintPDF import (
    activity_GeneratePreprintPDF as activity_class,
)
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
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
        activity_module.SLEEP_SECONDS = 0.001
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(github_provider, "find_github_issues")
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
        fake_find_github_issues,
    ):
        "test do_activity() returning a successful result"
        directory = TempDirectory()

        github_issue = FakeGithubIssue()
        fake_find_github_issues.return_value = [github_issue]

        expected_pdf_file_name = "elife-preprint-95901-v1.pdf"
        expected_pdf_s3_folder = (
            "expanded_meca/95901-v1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda/pdf/"
        )
        expected_pdf_s3_path = "%s%s" % (
            expected_pdf_s3_folder,
            expected_pdf_file_name,
        )

        # save pdf_s3_path value for assertion later then remove it from session
        session_dict = copy.copy(SESSION_DICT)
        pdf_s3_path = session_dict["pdf_s3_path"]
        del session_dict["pdf_s3_path"]
        # add meca details module name to the session
        session_dict["meca_details_module"] = "MecaDetails"

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, dest_folder=directory.path
        )

        session_object = FakeSession(session_dict)
        fake_session.return_value = session_object

        response = FakeResponse(
            200,
            content=b"pdf",
        )

        headers_kept = {
            "X-Info": "Some info",
            "X-Warnings": "Some warnings",
        }
        headers_all = copy.copy(headers_kept)
        headers_all["Content-Disposition"] = "attachment; filename=document.pdf"
        response.headers = headers_all
        fake_post.return_value = response

        expected_result = activity_class.ACTIVITY_SUCCESS

        expected_comment_body = (
            "elife-bot workflow message:\n\nGeneratePreprintPDF, response headers when generated"
            " %s: %s"
        ) % (expected_pdf_s3_path, json.dumps(headers_kept))

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertTrue(
            "GeneratePreprintPDF, endpoint url https://api/generate_preprint_pdf/"
            in self.activity.logger.loginfo,
        )
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
                " %s" % expected_pdf_file_name
            )
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "GeneratePreprintPDF, for article_id 95901 version 1 writing response content"
                " to %s/%s"
            )
            % (self.activity.directories.get("TEMP_DIR"), expected_pdf_file_name)
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "GeneratePreprintPDF, for article_id 95901 version 1"
                " uploading to pdf_expanded_folder: %s"
            )
            % expected_pdf_s3_folder
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "GeneratePreprintPDF, for article_id 95901 version 1 session pdf_s3_path: %s"
                % expected_pdf_s3_path
            )
            in self.activity.logger.loginfo,
        )

        # test session value was set
        self.assertEqual(session_object.get_value("pdf_s3_path"), pdf_s3_path)

        # test pdf file in S3 folder
        pdf_path = os.path.join(directory.path, pdf_s3_path)
        self.assertEqual(
            os.listdir(os.path.dirname(pdf_path)), [expected_pdf_file_name]
        )

        self.assertEqual(github_issue.comment.body, expected_comment_body)

    @patch.object(github_provider, "find_github_issues")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch("requests.post")
    def test_do_activity_post_publication(
        self,
        fake_post,
        fake_session,
        fake_storage_context,
        fake_outbox_storage_context,
        fake_find_github_issues,
    ):
        "test do_activity() successful result as a post-publication workflow"
        directory = TempDirectory()

        github_issue = FakeGithubIssue()
        fake_find_github_issues.return_value = [github_issue]

        session_dict = copy.copy(SESSION_DICT)
        # add meca details module name to the session
        session_dict["meca_details_module"] = "MecaPostPublicationDetails"

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, dest_folder=directory.path
        )

        session_object = FakeSession(session_dict)
        fake_session.return_value = session_object

        response = FakeResponse(
            200,
            content=b"pdf",
        )
        # test X-Info only in the headers
        headers_kept = {
            "X-Info": "Some info",
        }
        headers_all = copy.copy(headers_kept)
        headers_all["Content-Disposition"] = "attachment; filename=document.pdf"
        response.headers = headers_all
        fake_post.return_value = response

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assert no Github issue comment was added
        self.assertEqual(github_issue.comment, None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_to_preprint_pdf_endpoint")
    def test_do_activity_endpoint_exception(
        self,
        fake_post_to_endpoint,
        fake_session,
        fake_storage_context,
    ):
        "test if an exception is raised when generating PDF from the endpoint"
        directory = TempDirectory()

        # remove pdf_s3_path from session
        session_dict = copy.copy(SESSION_DICT)
        del session_dict["pdf_s3_path"]

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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

        fake_session.return_value = FakeSession(session_dict)
        expected_result = activity_class.ACTIVITY_TEMPORARY_FAILURE
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

    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_to_preprint_pdf_endpoint")
    def test_endpoint_exception_max_attempts(
        self,
        fake_post_to_endpoint,
        fake_session,
        fake_storage_context,
        fake_find_github_issues,
    ):
        "test if POST raises an exception and is the final attempt"
        directory = TempDirectory()

        github_issue = FakeGithubIssue()
        fake_find_github_issues.return_value = [github_issue]
        # remove pdf_s3_path from session
        session_dict = copy.copy(SESSION_DICT)
        # set the session counter value
        session_dict[activity_module.SESSION_ATTEMPT_COUNTER_NAME] = 1000000

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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

        fake_session.return_value = FakeSession(session_dict)
        expected_result = activity_class.ACTIVITY_SUCCESS
        expected_comment_body = (
            "elife-bot workflow message:\n\nGeneratePreprintPDF, POST to endpoint_url"
            " %s attempts reached MAX_ATTEMPTS of %s for file %s/content/24301711.xml"
        ) % (
            settings_mock.generate_preprint_pdf_api_endpoint,
            activity_module.MAX_ATTEMPTS,
            self.activity.directories.get("INPUT_DIR"),
        )

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintPDF, POST to endpoint_url"
                " %s attempts reached MAX_ATTEMPTS of %s for file %s/content/24301711.xml"
                % (
                    settings_mock.generate_preprint_pdf_api_endpoint,
                    activity_module.MAX_ATTEMPTS,
                    self.activity.directories.get("INPUT_DIR"),
                )
            ),
        )

        self.assertEqual(github_issue.comment.body, expected_comment_body)

    @patch("provider.preprint.generate_new_pdf_href")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch("requests.post")
    def test_do_activity_save_pdf_exception(
        self,
        fake_post,
        fake_session,
        fake_storage_context,
        fake_generate_new_pdf_href,
    ):
        "test and exception raised saving the PDF"
        directory = TempDirectory()

        # remove pdf_s3_path from session
        session_dict = copy.copy(SESSION_DICT)
        del session_dict["pdf_s3_path"]

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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

        session_object = FakeSession(session_dict)
        fake_session.return_value = session_object

        fake_post.return_value = FakeResponse(
            200,
            content=b"pdf",
        )

        exception_message = "An exception"
        fake_generate_new_pdf_href.side_effect = Exception(exception_message)

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on log
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintPDF, for article_id 95901 version 1"
                " exception raised saving PDF to disk: %s"
            )
            % exception_message,
        )

    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch("requests.post")
    def test_do_activity_upload_to_s3_exception(
        self,
        fake_post,
        fake_session,
        fake_storage_context,
        fake_outbox_storage_context,
    ):
        "test an exception raised uploading the PDF to the S3 expanded folder"
        directory = TempDirectory()

        # remove pdf_s3_path from session
        session_dict = copy.copy(SESSION_DICT)
        del session_dict["pdf_s3_path"]

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
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
        exception_message = "An exception"
        fake_outbox_storage_context.side_effect = Exception(exception_message)

        session_object = FakeSession(session_dict)
        fake_session.return_value = session_object

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
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintPDF, for article_id 95901 version 1 exception raised"
                " uploading PDF to S3: %s"
            )
            % exception_message,
        )

        # test session value was not set
        self.assertEqual(session_object.get_value("pdf_s3_path"), None)


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


class TestGetWorkflowType(unittest.TestCase):
    "tests for get_workflow_type()"

    def test_pre_publication(self):
        # invoke
        result = activity_module.get_workflow_type("MecaDetails")
        # assert
        self.assertEqual(result, "pre-publication")

    def test_post_publication(self):
        # invoke
        result = activity_module.get_workflow_type("MecaPostPublicationDetails")
        # assert
        self.assertEqual(result, "post-publication")

    def test_no_match(self):
        # invoke
        result = activity_module.get_workflow_type(None)
        # assert
        self.assertEqual(result, None)


class TestFilterResponseHeaders(unittest.TestCase):
    "tests for filter_response_headers()"

    def test_filter_response_headers(self):
        "test filtering response header values"
        headers = {
            "Content-Disposition": "attachment; filename=document.pdf",
            "X-Info": "Some info",
            "X-Warnings": "Some warnings",
        }
        # invoke
        result = activity_module.filter_response_headers(headers)
        # assert
        self.assertDictEqual(
            result,
            {
                "X-Info": "Some info",
                "X-Warnings": "Some warnings",
            },
        )
