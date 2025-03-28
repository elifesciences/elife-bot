# coding=utf-8

import copy
import os
import glob
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_AcceptedSubmissionPeerReviews as activity_module
from activity.activity_AcceptedSubmissionPeerReviews import (
    activity_AcceptedSubmissionPeerReviews as activity_object,
)
from tests import read_fixture
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestAcceptedSubmissionPeerReviews(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(test_activity_data.accepted_session_example))
        self.session.store_value("prc_status", True)
        self.session.store_value("docmap_string", read_fixture("2021.06.02.446694.docmap.json"))
        self.session.store_value(
            "preprint_url", "https://doi.org/10.1101/2021.06.02.446694"
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)
        self.session.store_value("docmap_string", None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch("requests.get")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_xml_root_status": True,
            "expected_upload_xml_status": True,
            "expected_log_warning_count": 2,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_get,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

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

        # add version DOI article-id to the XML file
        version_doi = "10.7554/eLife.45644.2"
        version_doi_xml = (
            '<article-id pub-id-type="doi" specific-use="version">'
            "%s</article-id>" % version_doi
        )
        sub_folder = test_data.get("filename").rsplit(".", 1)[0]
        xml_path = os.path.join(
            directory.path,
            self.session.get_value("expanded_folder"),
            sub_folder,
            "%s.xml" % sub_folder,
        )
        with open(xml_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
        with open(xml_path, "w", encoding="utf-8") as open_file:
            xml_string = xml_string.replace(
                "<article-meta>", "<article-meta>%s" % version_doi_xml
            )
            open_file.write(xml_string)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, True)

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")

        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        with open(xml_file_path, "r") as open_file:
            xml_content = open_file.read()
        # assert found number of sub-article tags in the XML
        self.assertTrue(xml_content.count("<sub-article") == 5)

        # assert peer review DOI value
        self.assertTrue(
            '<article-id pub-id-type="doi">%s.sa0</article-id>' % version_doi
            in xml_content
        )

        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            test_data.get("expected_docmap_string_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("xml_root"),
            test_data.get("expected_xml_root_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()

        self.assertTrue(
            "elifecleaner:sub_article:add_sub_article_xml: Parsing article XML into root Element"
            in log_contents
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_log_warning_count": 2,
        },
    )
    def test_do_activity_not_prc_status(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        # reset prc_status from the session
        self.session.store_value("prc_status", None)
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

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
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, True)
