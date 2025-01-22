from datetime import datetime
import json
import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import cleaner, docmap_provider, meca, utils
from activity import activity_ExpandMeca as activity_module
from activity.activity_ExpandMeca import (
    activity_ExpandMeca as activity_class,
)
from tests import list_files, read_fixture
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import FakeLogger, FakeStorageContext, FakeSession


class TestExpandMeca(unittest.TestCase):
    "tests for do_activity()"

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(utils, "get_current_datetime")
    def test_do_activity(
        self,
        fake_datetime,
        fake_get_docmap,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_files = [
            "content/24301711.pdf",
            "content/24301711.xml",
            "content/24301711v1_fig1.tif",
            "content/24301711v1_tbl1.tif",
            "content/24301711v1_tbl1a.tif",
            "content/24301711v1_tbl2.tif",
            "content/24301711v1_tbl3.tif",
            "content/24301711v1_tbl4.tif",
            "directives.xml",
            "manifest.xml",
            "mimetype",
            "transfer.xml",
        ]
        expected_session_dict = test_activity_data.ingest_meca_session_example()
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # Check destination folder files
        bucket_folder_path = os.path.join(
            directory.path,
            mock_session.session_dict.get("expanded_folder"),
        )
        # collect bucket folder file names plus one folder deep file names
        files = list_files(bucket_folder_path)
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(sorted(compare_files), sorted(expected_files))
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "ExpandMeca expanding file %s/95901-v1-meca.zip"
            % self.activity.directories.get("INPUT_DIR")
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

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(activity_module.download_helper, "download_file_from_s3")
    def test_download_meca_activity_exception(
        self, fake_download, fake_get_docmap, fake_storage_context, fake_session
    ):
        "test an exception during the download procedure"
        directory = TempDirectory()
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        fake_download.side_effect = Exception("Message")
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(meca, "get_meca_article_xml_path")
    def test_no_article_xml_path(
        self,
        fake_get_meca_article_xml_path,
        fake_get_docmap,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
    ):
        "test if no article XML is found in manifest.xml"
        directory = TempDirectory()
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        fake_get_meca_article_xml_path.return_value = None
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)


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


class TestComputerFileUrlFromSteps(unittest.TestCase):
    "tests for computer_file_url_from_steps()"

    def setUp(self):
        self.caller_name = "test"
        self.version_doi = "10.7554/eLife.95901.1"
        self.logger = FakeLogger()

    def test_computer_file_url_from_steps(self):
        "test simple docmap steps data returning a MECA computer-file URL"
        meca_url = "s3://example/example.meca"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [{"type": "computer-file", "url": meca_url}],
                    }
                ]
            }
        ]
        result = activity_module.computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, meca_url)

    def test_none(self):
        "test no computer-file URL data"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [{"type": "computer-file"}],
                    }
                ]
            }
        ]
        expected = None
        result = activity_module.computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, expected)

    def test_exception(self):
        "test raising exception"
        steps = None
        with self.assertRaises(TypeError):
            activity_module.computer_file_url_from_steps(
                steps, self.version_doi, self.caller_name, self.logger
            )
