# coding=utf-8

import unittest
import copy
import json
import os
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider, meca, preprint
import activity.activity_ValidatePreprintSchematron as activity_module
from activity.activity_ValidatePreprintSchematron import (
    activity_ValidatePreprintSchematron as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeStorageContext,
    FakeSession,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()

EXAMPLE_RESPONSE_CONTENT = {"results": {"errors": [], "warnings": []}}

EXAMPLE_ERROR_RESPONSE_CONTENT = {
    "results": {
        "errors": [
            {
                "path": "\\/article[1]\\/back[1]\\/ref-list[1]\\/ref[33]\\/mixed-citation[1]",
                "type": "error",
                "message": (
                    "[journal-ref-article-title] This journal reference "
                    "(id c33) has no article-title element."
                ),
            },
        ],
        "warnings": [
            {
                "path": "\\/article[1]\\/back[1]\\/sec[5]\\/p[1]",
                "type": "warning",
                "message": (
                    "[p-all-bold] Content of p element is entirely in bold - "
                    "'Figure S1. Clinical information and genetic analysis of "
                    "CTRL and WS donors.'. Is this correct?"
                ),
            },
            {
                "path": "\\/article[1]\\/back[1]\\/sec[5]\\/p[6]",
                "type": "info",
                "message": (
                    "[p-all-bold] Content of p element is entirely in bold - "
                    "'Figure S2. Characterization of primary cells and the "
                    "generated iPSCs.'. Is this correct?"
                ),
            },
        ],
    }
}


class TestValidatePreprintSchematron(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        activity_module.SLEEP_SECONDS = 0.001
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        directory = TempDirectory()
        github_issue = FakeGithubIssue()
        fake_find_github_issues.return_value = [github_issue]
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        validation_content = bytes(
            json.dumps(EXAMPLE_RESPONSE_CONTENT), encoding="utf-8"
        )
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_SUCCESS
        expected_comment_body = "```diff\n(No schematron messages)\n```"
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(self.activity.statuses.get("results"), True)
        self.assertEqual(github_issue.comment.body, expected_comment_body)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_post_xml_file_content_empty(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST response content returned is empty"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = b"{}"
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(preprint, "modify_xml_namespaces")
    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_xml_namespaces_exception(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
        fake_modify_xml_namespaces,
    ):
        "test if modifying XML namespaces raises an exception"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = b"{}"
        fake_modify_xml_namespaces.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception raised in modify_xml_namespaces for file %s:"
                " An exception"
            )
            % (
                self.activity.name,
                os.path.join(
                    self.activity.directories.get("INPUT_DIR"), "content/24301711.xml"
                ),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_post_xml_file_exception(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST raises an exception"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        mock_session = FakeSession(SESSION_DICT)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_TEMPORARY_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_invalid_response(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        "test blank response content"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        validation_content = b""
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_TEMPORARY_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_github_exception(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        "test if Github communication raises an error"
        directory = TempDirectory()
        fake_find_github_issues.side_effect = [Exception("An exception")]
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        xml_string = b"<root/>"
        validation_content = bytes(
            json.dumps(EXAMPLE_ERROR_RESPONSE_CONTENT), encoding="utf-8"
        )
        with open(destination_path, "wb") as open_file:
            open_file.write(xml_string)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.return_value = validation_content
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception when adding a comment to Github for version DOI %s - "
                "Details: An exception"
            )
            % (
                self.activity.name,
                SESSION_DICT.get("version_doi"),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(meca, "post_xml_file")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    def test_post_to_xsl_exception_max_attempts(
        self,
        fake_storage_context,
        fake_find_github_issues,
        fake_post_xml_file,
        fake_session,
    ):
        "test if POST raises an exception and is the final attempt"
        directory = TempDirectory()
        fake_find_github_issues.side_effect = Exception("An exception")
        mock_session = FakeSession(copy.copy(SESSION_DICT))
        # set the session counter value
        mock_session.store_value(activity_module.SESSION_ATTEMPT_COUNTER_NAME, 1000000)
        fake_session.return_value = mock_session
        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        start_xml = b"<root/>"
        with open(destination_path, "wb") as open_file:
            open_file.write(start_xml)
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path,
            dest_folder=directory.path,
            resources=[SESSION_DICT.get("article_xml_path")],
        )
        fake_post_xml_file.side_effect = Exception("An exception")
        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)


class TestMissingSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.preprint_schematron_endpoint = settings_mock.preprint_schematron_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.preprint_schematron_endpoint = self.preprint_schematron_endpoint

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.preprint_schematron_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "ValidatePreprintSchematron, "
                "preprint_schematron_endpoint in settings is missing, skipping"
            ),
        )


class TestBlankSettings(unittest.TestCase):
    "test if required settings are blank"

    def setUp(self):
        self.preprint_schematron_endpoint = settings_mock.preprint_schematron_endpoint

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.preprint_schematron_endpoint = self.preprint_schematron_endpoint

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.preprint_schematron_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity()
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "ValidatePreprintSchematron, "
                "preprint_schematron_endpoint in settings is blank, skipping"
            ),
        )


class TestComposeValidationMessage(unittest.TestCase):
    "test for compose_validation_message()"

    def test_compose_validation_message(self):
        "test formatting of errors and warnings"
        errors = EXAMPLE_ERROR_RESPONSE_CONTENT.get("results").get("errors")
        warnings = EXAMPLE_ERROR_RESPONSE_CONTENT.get("results").get("warnings")
        expected = "\n".join(
            [
                (
                    "error: [journal-ref-article-title] "
                    "This journal reference (id c33) has no article-title element."
                ),
                (
                    "warning: [p-all-bold] Content of p element is entirely in bold - "
                    "'Figure S1. Clinical information and "
                    "genetic analysis of CTRL and WS donors.'. "
                    "Is this correct?"
                ),
                (
                    "info: [p-all-bold] Content of p element is entirely in bold - "
                    "'Figure S2. Characterization of"
                    " primary cells and the generated iPSCs.'. "
                    "Is this correct?"
                ),
            ]
        )
        result = activity_module.compose_validation_message(errors, warnings)
        self.assertEqual(result, expected)

    def test_blank_result(self):
        "if no errors or warnings"
        errors = []
        warnings = []
        expected = "(No schematron messages)"
        result = activity_module.compose_validation_message(errors, warnings)
        self.assertEqual(result, expected)


class TestEnhanceValidationMessage(unittest.TestCase):
    "test for enhance_validation_message()"

    def test_enhance_validation_message(self):
        "test additional formatting of errors and warnings"
        log_message = "\n".join(
            [
                ("error: [journal-ref-article-title] ..."),
                ("warning: [p-all-bold] Content of p element ..."),
                ("info: [p-all-bold] Content of p element is entirely ..."),
            ]
        )
        expected = (
            "```diff\n"
            "- error: [journal-ref-article-title] ...\n"
            "! warning: [p-all-bold] Content of p element ...\n"
            "+ info: [p-all-bold] Content of p element is entirely ...\n"
            "```"
        )
        result = activity_module.enhance_validation_message(
            log_message, enhance_message=True
        )
        self.assertEqual(result, expected)

    def test_blank_result(self):
        "if no errors or warnings"
        log_message = "(No schematron messages)"
        expected = "```diff\n(No schematron messages)\n```"
        result = activity_module.enhance_validation_message(
            log_message, enhance_message=True
        )
        self.assertEqual(result, expected)

    def test_no_message_enhancement(self):
        "test if no additional enhancement is added"
        log_message = "(No schematron messages)"
        expected = "```\n(No schematron messages)\n```"
        result = activity_module.enhance_validation_message(
            log_message, enhance_message=False
        )
        self.assertEqual(result, expected)
