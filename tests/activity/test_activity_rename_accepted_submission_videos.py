# coding=utf-8

import os
import glob
import copy
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_RenameAcceptedSubmissionVideos as activity_module
from activity.activity_RenameAcceptedSubmissionVideos import (
    activity_RenameAcceptedSubmissionVideos as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


def session_data(filename=None, article_id=None, deposit_videos=None):
    s_data = copy.copy(test_activity_data.accepted_session_example)
    if filename:
        s_data["input_filename"] = filename
    if article_id:
        s_data["article_id"] = article_id
    if deposit_videos:
        s_data["deposit_videos"] = deposit_videos
    return s_data


@ddt
class TestRenameAcceptedSubmissionVideos(unittest.TestCase):
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
            "comment": "accepted submission with videos",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "article_id": "63532",
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_rename_videos_status": True,
            "expected_modify_xml_status": True,
            "expected_upload_xml_status": True,
            "expected_file_count": 26,
            "expected_files": ["elife-63532-video1.avi", "elife-63532-video2.avi"],
        },
        {
            "comment": "accepted submission zip has no videos",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "article_id": "45644",
            "expected_xml_file_path": "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "expected_result": True,
            "expected_rename_videos_status": None,
            "expected_modify_xml_status": None,
            "expected_upload_xml_status": None,
            "expected_file_count": 42,
            "expected_files": [],
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
        workflow_session_data = session_data(
            filename=test_data.get("filename"),
            article_id=test_data.get("article_id"),
            deposit_videos=True,
        )
        fake_session.return_value = FakeSession(workflow_session_data)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")

        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            test_data.get("expected_xml_file_path"),
        )
        self.assertTrue(xml_file_path in temp_dir_files)

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
            self.activity.statuses.get("rename_videos"),
            test_data.get("expected_rename_videos_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("modify_xml"),
            test_data.get("expected_modify_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # some assertions on the bucket folder contents and the XML <file> tag values
        expanded_path = os.path.join(
            directory.path,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            test_data.get("filename").rstrip(".zip"),
        )
        expanded_files = os.listdir(expanded_path)
        self.assertEqual(len(expanded_files), test_data.get("expected_file_count"))
        for expected_file in test_data.get("expected_files"):
            self.assertTrue(
                expected_file in expanded_files,
                "file {expected_file} not found in expanded_files in {comment}".format(
                    expected_file=expected_file, comment=test_data.get("comment")
                ),
            )

        # reset REPAIR_XML value
        activity_module.REPAIR_XML = False

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    def test_do_activity_deposit_videos_none(
        self,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is no deposit_videos value in the session"
        directory = TempDirectory()
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(session_data(zip_file, article_id))
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
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_loginfo = (
            "RenameAcceptedSubmissionVideos, %s"
            " deposit_videos session value is None, activity returning True"
        ) % zip_file
        self.assertEqual(self.activity.logger.loginfo[-1], expected_loginfo)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "file_list")
    def test_do_activity_exception_parseerror(
        self,
        fake_file_list,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an XML ParseError when getting a file list"
        directory = TempDirectory()
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base
        xml_file = "%s/%s.xml" % (zip_file_base, zip_file_base)
        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            xml_file,
        )

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, deposit_videos=True)
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
        fake_file_list.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "RenameAcceptedSubmissionVideos, XML ParseError exception "
            "parsing file %s for file %s"
        ) % (xml_file_path, zip_file)
        self.assertEqual(self.activity.logger.logexception, expected_logexception)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "video_data_from_files")
    def test_do_activity_video_data_exception(
        self,
        fake_video_data_from_files,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an exception generating video file names"
        directory = TempDirectory()
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, deposit_videos=True)
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
        fake_video_data_from_files.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "RenameAcceptedSubmissionVideos, exception invoking video_data_from_files "
            "for file %s"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_logexception)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "xml_rewrite_file_tags")
    def test_do_activity_xml_rewrite_exception(
        self,
        fake_xml_rewrite_file_tags,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an exception rewriting the XML file"
        directory = TempDirectory()
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, deposit_videos=True)
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
        fake_xml_rewrite_file_tags.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "RenameAcceptedSubmissionVideos, exception invoking xml_rewrite_file_tags "
            "for file %s"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_logexception)
