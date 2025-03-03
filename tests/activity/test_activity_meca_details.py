from datetime import datetime
import copy
import json
import unittest
from mock import patch
from provider import cleaner, docmap_provider, utils
from activity import activity_MecaDetails as activity_module
from activity.activity_MecaDetails import (
    activity_MecaDetails as activity_class,
)
from tests import read_fixture, test_data
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
)


class TestMecaDetails(unittest.TestCase):
    "tests for do_activity()"

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(utils, "get_current_datetime")
    def test_do_activity(
        self,
        fake_datetime,
        fake_get_docmap,
        fake_session,
    ):
        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_session_dict = test_activity_data.meca_details_session_example()
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "MecaDetails, computer_file_url s3://prod-elife-epp-meca/95901-v1-meca.zip"
            " for version_doi 10.7554/eLife.95901.1"
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(utils, "get_current_datetime")
    def test_silent_correction(
        self,
        fake_datetime,
        fake_get_docmap,
        fake_session,
    ):
        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        computer_file_url = (
            "s3://test-elife-epp-meca/silent-corrections/95901-v1-meca.zip"
        )
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_session_dict = test_activity_data.meca_details_session_example(
            run_type="silent-correction", computer_file_url=computer_file_url
        )
        # silent-correction run_type
        input_data = copy.copy(test_data.silent_ingest_meca_data)
        input_data["run_type"] = "silent-correction"
        # do the activity
        result = self.activity.do_activity(input_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "MecaDetails, computer_file_url %s"
            " for version_doi 10.7554/eLife.95901.1" % computer_file_url
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_get_docmap_exception(self, fake_get_docmap, fake_session):
        "test exception is raised when getting docmap string"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        fake_get_docmap.side_effect = Exception("An exception")
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        expected_docmap_string_status = None
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            expected_docmap_string_status,
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_parse_docmap_string_exception(self, fake_get_docmap, fake_session):
        "test exception is raised parsing the docmap string"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        fake_get_docmap.return_value = b"{"
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception parsing docmap_string for article_id %s: "
                "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
            )
            % (self.activity.name, mock_session.session_dict.get("article_id")),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(docmap_provider, "version_doi_step_map")
    def test_step_map_exception(self, fake_step_map, fake_get_docmap, fake_session):
        "test exception is raised getting a step map from the docmap"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        exception_message = "An exception"
        fake_step_map.side_effect = Exception(exception_message)
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "%s, exception in steps_by_version_doi for version DOI 10.7554/eLife.%s.%s: %s"
            )
            % (
                self.activity.name,
                mock_session.session_dict.get("article_id"),
                mock_session.session_dict.get("version"),
                exception_message,
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_no_steps(self, fake_get_docmap, fake_session):
        "test if there are no steps for the version DOI"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        # load a docmap with a mismatched version DOI
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_87445.json")
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            ("%s, found no docmap steps for version DOI 10.7554/eLife.%s.%s")
            % (
                self.activity.name,
                mock_session.session_dict.get("article_id"),
                mock_session.session_dict.get("version"),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_no_computer_file(self, fake_get_docmap, fake_session):
        "test if there is no computer-file value in the docmap"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        docmap_string = read_fixture("sample_docmap_for_95901.json")
        # modify the test fixture to have no computer-file keys
        fake_get_docmap.return_value = docmap_string.replace(
            b"computer-file", b"not-a-computer-file"
        )
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                (
                    "%s, computer_file_url not found in computer_file "
                    "for version DOI 10.7554/eLife.%s.%s"
                )
            )
            % (
                self.activity.name,
                mock_session.session_dict.get("article_id"),
                mock_session.session_dict.get("version"),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_no_computer_file_url(self, fake_get_docmap, fake_session):
        "test if there is no computer-file url value in the docmap"
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        docmap_string = read_fixture("sample_docmap_for_95901.json")
        docmap_json = json.loads(docmap_string)
        # modify the test fixture computer-file url value
        del docmap_json["steps"]["_:b0"]["inputs"][0]["content"][0]["url"]
        fake_get_docmap.return_value = bytes(json.dumps(docmap_json), encoding="utf-8")
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                (
                    "%s, computer_file_url not found in "
                    "computer_file for version DOI 10.7554/eLife.%s.%s"
                )
            )
            % (
                self.activity.name,
                mock_session.session_dict.get("article_id"),
                mock_session.session_dict.get("version"),
            ),
        )


class TestMecaFileParts(unittest.TestCase):
    "tests for meca_file_parts()"

    def test_meca_file_parts(self):
        "test getting data from a typical MECA zip file name"
        file_name = "95901-v1-meca.zip"
        expected_article_id = 95901
        expected_version = "1"
        # invoke
        result = activity_module.meca_file_parts(file_name)
        # assert
        self.assertEqual(result[0], expected_article_id)
        self.assertEqual(result[1], expected_version)


class TestStepsByVersionDoi(unittest.TestCase):
    "tests for steps_by_version_doi()"

    def setUp(self):
        self.caller_name = "test"
        self.version_doi = "10.7554/eLife.95901.1"
        self.logger = FakeLogger()

    def test_steps_by_version_doi(self):
        "test with valid docmap JSON"
        docmap_json = json.loads(read_fixture("sample_docmap_for_95901.json"))
        expected_len = 3
        expected_0_keys = ["actions", "assertions", "inputs", "next-step"]
        result = activity_module.steps_by_version_doi(
            docmap_json, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(len(result), expected_len)
        self.assertEqual(sorted(list(result[0].keys())), sorted(expected_0_keys))

    def test_exception(self):
        "test raising an exception"
        docmap_json = "foo"
        with self.assertRaises(AttributeError):
            activity_module.steps_by_version_doi(
                docmap_json, self.version_doi, self.caller_name, self.logger
            )
        self.assertEqual(
            self.logger.logexception,
            (
                "%s, exception getting a step map for version DOI %s: "
                "'str' object has no attribute 'get'"
            )
            % (self.caller_name, self.version_doi),
        )
