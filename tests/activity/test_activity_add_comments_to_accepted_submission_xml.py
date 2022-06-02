# coding=utf-8

import os
import glob
import copy
import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_AddCommentsToAcceptedSubmissionXml as activity_module
from activity.activity_AddCommentsToAcceptedSubmissionXml import (
    activity_AddCommentsToAcceptedSubmissionXml as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = copy.copy(test_case_data.ingest_accepted_submission_data)
    activity_data["file_name"] = file_name_to_change
    return activity_data


def session_data(filename=None, article_id=None, cleaner_log=None):
    s_data = copy.copy(test_activity_data.accepted_session_example)
    if filename:
        s_data["input_filename"] = filename
    if article_id:
        s_data["article_id"] = article_id
    if cleaner_log:
        s_data["cleaner_log"] = cleaner_log
    return s_data


@ddt
class TestAddCommentsToAcceptedSubmissionXml(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission cleaner_log includes a warning",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "article_id": "45644",
            "cleaner_log": (
                "2022-03-31 11:11:39,706 "
                "WARNING elifecleaner:parse:check_multi_page_figure_pdf: "
                "30-01-2019-RA-eLife-45644.zip multiple page PDF figure file: "
                "30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf\n"
            ),
            "expected_xml_file_path": "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "expected_result": True,
            "expected_add_status": True,
            "expected_upload_xml_status": True,
            "expected_xml": [
                (
                    "<production-comments>"
                    "<p>Exeter: &quot;Appendix 1figure 10.pdf&quot; is a PDF file made up of "
                    "more than one page. Please check if there are images on numerous pages. "
                    "If that's the case, please add the following author query: "
                    "&quot;Please provide this figure in a single-page format. If this would "
                    "render the figure unreadable, please provide this as separate figures or "
                    "figure supplements.&quot;</p></production-comments>"
                )
            ],
        },
        {
            "comment": "accepted submission cleaner_log is blank",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "article_id": "45644",
            "cleaner_log": "",
            "expected_xml_file_path": None,
            "expected_result": True,
            "expected_add_status": None,
            "expected_upload_xml_status": None,
            "expected_xml": [],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_storage_context,
        fake_session,
    ):
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        workflow_session_data = session_data(
            filename=test_data.get("filename"),
            article_id=test_data.get("article_id"),
            cleaner_log=test_data.get("cleaner_log"),
        )
        fake_session.return_value = FakeSession(workflow_session_data)

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
            directory.path, resources
        )

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

        self.assertEqual(
            self.activity.statuses.get("add"),
            test_data.get("expected_add_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        expanded_folder = os.path.join(
            directory.path, workflow_session_data.get("expanded_folder")
        )
        expanded_folder_files = glob.glob(expanded_folder + "/*/*")
        xml_file_path = ""
        if test_data.get("expected_xml_file_path"):
            xml_file_path = os.path.join(
                expanded_folder,
                test_data.get("expected_xml_file_path"),
            )
            self.assertTrue(xml_file_path in expanded_folder_files)

        if xml_file_path and test_data.get("expected_xml"):
            # assert XML file was modified
            with open(xml_file_path, "r", encoding="utf-8") as open_file:
                xml_string = open_file.read()
            for expected_xml in test_data.get("expected_xml"):
                self.assertTrue(
                    expected_xml in xml_string,
                    "%s not found in xml_string" % expected_xml,
                )

        # reset REPAIR_XML value
        activity_module.REPAIR_XML = False

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "parse_article_xml")
    def test_do_activity_exception_parseerror(
        self,
        fake_parse_article_xml,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an XML ParseError when parsing it"
        directory = TempDirectory()
        zip_file_base = "30-01-2019-RA-eLife-45644"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base
        xml_file = "%s/%s.xml" % (zip_file_base, zip_file_base)
        xml_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"),
            xml_file,
        )

        fake_session.return_value = FakeSession(
            session_data(
                zip_file, article_id, cleaner_log=" WARNING elifecleaner:parse:foo: bar"
            )
        )
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_file,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_parse_article_xml.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "AddCommentsToAcceptedSubmissionXml, XML ParseError exception "
            "parsing XML %s for file %s"
        ) % (xml_file_path, zip_file)

        self.assertEqual(self.activity.logger.logexception, expected_logexception)


class TestAddXmlException(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "add_comments_to_xml")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_xml_exception(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_add_comments_to_xml,
        fake_storage_context,
    ):
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True

        directory = TempDirectory()
        filename = "30-01-2019-RA-eLife-45644.zip"
        article_id = "45644"

        workflow_session_data = session_data(
            filename=filename,
            article_id=article_id,
            cleaner_log=" WARNING elifecleaner:parse:foo: bar",
        )
        fake_session.return_value = FakeSession(workflow_session_data)

        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            filename,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            workflow_session_data.get("expanded_folder"),
            zip_file_path,
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        fake_add_comments_to_xml.side_effect = Exception("An exception")
        result = self.activity.do_activity(input_data(filename))
        self.assertEqual(result, True)
        self.assertTrue(
            self.activity.logger.logexception.startswith(
                "AddCommentsToAcceptedSubmissionXml, exception in add_comments_to_xml"
            )
        )

        # reset REPAIR_XML value
        activity_module.REPAIR_XML = False


class TestAddCommentsToXml(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_comments_to_xml(self):
        "test adding missing tags to a basic XML file"
        directory = TempDirectory()
        xml_file_path = os.path.join(directory.path, "test.xml")
        xml_string = "<article><front><article-meta/></front></article>"
        comments = ["A comment"]
        input_filename = "test.zip"
        expected = (
            '<?xml version="1.0" ?>'
            "<article><front><article-meta>"
            "<custom-meta-group>"
            "<production-comments><p>A comment</p></production-comments>"
            "</custom-meta-group>"
            "</article-meta></front></article>"
        )
        root = ElementTree.fromstring(xml_string)
        activity_module.add_comments_to_xml(
            root, xml_file_path, comments, input_filename
        )
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            output_xml = open_file.read()
        self.assertEqual(output_xml, expected)
