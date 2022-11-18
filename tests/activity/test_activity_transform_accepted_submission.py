# coding=utf-8

import os
import copy
import shutil
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from provider import cleaner
import activity.activity_TransformAcceptedSubmission as activity_module
from activity.activity_TransformAcceptedSubmission import (
    activity_TransformAcceptedSubmission as activity_object,
)
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
from tests.activity import helpers, settings_mock, test_activity_data
import tests.test_data as test_case_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


class TestTransformAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self, fake_storage_context, fake_cleaner_storage_context, fake_session
    ):
        test_data = {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_transform_status": True,
        }
        directory = TempDirectory()
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True

        # copy files into the input directory using the storage context
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
        dest_folder = os.path.join(directory.path, "files_dest")
        os.mkdir(dest_folder)
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
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
                input_file=test_data.get("filename"),
                filename=filename_used,
            ),
        )

        self.assertEqual(
            self.activity.statuses.get("transform"),
            test_data.get("expected_transform_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        log_infos = [
            line
            for line in log_contents.split("\n")
            if "INFO elifecleaner:transform:" in line
        ]
        # check output bucket folder contents
        bucket_folder_path = os.path.join(
            dest_folder,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            "30-01-2019-RA-eLife-45644",
        )
        output_bucket_list = [
            file_name
            for file_name in os.listdir(bucket_folder_path)
            if file_name != ".gitkeep"
        ]
        self.assertEqual(
            sorted(output_bucket_list),
            ["30-01-2019-RA-eLife-45644.xml", "Figure 5source code 1.c.zip"],
        )

        # compare some log file values,
        # these assertions can be removed if any are too hard to manage
        self.assertTrue(
            log_infos[0].endswith(
                "30-01-2019-RA-eLife-45644.zip code_file_name: Figure 5source code 1.c"
            )
        )
        self.assertTrue(
            log_infos[1].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip from_file: "
                    'ArticleZipFile("Figure 5source code 1.c", '
                    '"30-01-2019-RA-eLife-45644/Figure 5source code 1.c", '
                    '"%s/30-01-2019-RA-eLife-45644/Figure 5source code 1.c")'
                )
                % self.activity.directories.get("INPUT_DIR")
            )
        )
        self.assertTrue(
            log_infos[2].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip to_file: "
                    'ArticleZipFile("Figure 5source code 1.c.zip", '
                    '"30-01-2019-RA-eLife-45644/Figure 5source code 1.c.zip", '
                    '"%s/Figure 5source code 1.c.zip")'
                )
                % self.activity.directories.get("TEMP_DIR")
            )
        )
        self.assertTrue(
            log_infos[4].endswith("30-01-2019-RA-eLife-45644.zip rewriting xml tags")
        )
        self.assertTrue(
            log_infos[5].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip writing xml to file "
                    "%s/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
                )
                % self.activity.directories.get("INPUT_DIR")
            )
        )
        self.assertTrue(
            log_infos[6].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip article_type research-article, "
                    "display_channel ['Research Article']"
                )
            )
        )
        self.assertTrue(
            log_infos[8].endswith(
                (
                    "30-01-2019-RA-eLife-45644.zip writing xml to file "
                    "%s/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
                )
                % self.activity.directories.get("INPUT_DIR")
            )
        )

        # check the zipped code file name is in the XML file
        xml_file_path = os.path.join(
            bucket_folder_path,
            "30-01-2019-RA-eLife-45644.xml",
        )
        with open(xml_file_path, "r", encoding="utf8") as open_file:
            xml_contents = open_file.read()
        self.assertTrue("Figure 5source code 1.c.zip" in xml_contents)
        self.assertTrue("<elocation-id>e45644</elocation-id>" in xml_contents)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_prc_status(
        self, fake_storage_context, fake_cleaner_storage_context, fake_session
    ):
        test_data = {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_transform_status": True,
        }
        session_data = copy.copy(test_activity_data.accepted_session_example)
        session_data["prc_status"] = True
        directory = TempDirectory()
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True

        # copy files into the input directory using the storage context
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
        dest_folder = os.path.join(directory.path, "files_dest")
        os.mkdir(dest_folder)
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        # mock the session
        fake_session.return_value = FakeSession(session_data)

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
                input_file=test_data.get("filename"),
                filename=filename_used,
            ),
        )

        self.assertEqual(
            self.activity.statuses.get("transform"),
            test_data.get("expected_transform_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        log_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.activity_log_file
        )
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()

        log_infos = [
            line
            for line in log_contents.split("\n")
            if "INFO elifecleaner:prc:" in line
        ]
        # check output bucket folder contents
        bucket_folder_path = os.path.join(
            dest_folder,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            "30-01-2019-RA-eLife-45644",
        )
        # compare some log file values,
        # these assertions can be removed if any are too hard to manage
        self.assertTrue(
            log_infos[0].endswith(
                ("replacing journal-id tag text of type nlm-ta to elife")
            )
        )
        self.assertTrue(
            log_infos[1].endswith(
                ("replacing journal-id tag text of type hwp to eLife")
            )
        )
        self.assertTrue(
            log_infos[2].endswith(
                ("replacing journal-id tag text of type publisher-id to eLife")
            )
        )
        self.assertTrue(
            log_infos[3].endswith(("changing elocation-id value e45644 to RP45644"))
        )

        # check the zipped code file name is in the XML file
        xml_file_path = os.path.join(
            bucket_folder_path,
            "30-01-2019-RA-eLife-45644.xml",
        )
        with open(xml_file_path, "r", encoding="utf8") as open_file:
            xml_contents = open_file.read()

        self.assertTrue(
            '<journal-id journal-id-type="publisher-id">eLife</journal-id>'
            in xml_contents
        )
        self.assertTrue("<elocation-id>RP45644</elocation-id>" in xml_contents)
        self.assertTrue(
            (
                '<custom-meta specific-use="meta-only">'
                "<meta-name>publishing-route</meta-name><meta-value>prc</meta-value>"
                "</custom-meta>"
            )
            in xml_contents
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "code_file_list")
    def test_do_activity_parse_exception(
        self,
        fake_code_file_list,
        fake_cleaner_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True
        filename_base = "30-01-2019-RA-eLife-45644"
        zip_filename = "%s.zip" % filename_base
        xml_filename = "%s.xml" % filename_base
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_filename,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )

        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )

        fake_code_file_list.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_filename))
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                (
                    "TransformAcceptedSubmission, XML ParseError exception in "
                    "download_code_files_from_bucket parsing XML file %s for file %s"
                )
                % (xml_filename, zip_filename)
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "transform_ejp_files")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_transform_exception(
        self,
        fake_storage_context,
        fake_transform_ejp_files,
        fake_cleaner_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True

        zip_filename = "30-01-2019-RA-eLife-45644.zip"
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_filename,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        # mock the session
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )

        fake_transform_ejp_files.side_effect = Exception()
        # do the activity
        result = self.activity.do_activity(input_data(zip_filename))
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                (
                    "TransformAcceptedSubmission, unhandled exception in "
                    "cleaner.transform_ejp_files for file %s"
                )
                % zip_filename
            ),
        )
