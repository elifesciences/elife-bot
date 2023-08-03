# coding=utf-8

import os
import glob
import copy
import shutil
import unittest
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_ValidateAcceptedSubmissionVideos as activity_module
from activity.activity_ValidateAcceptedSubmissionVideos import (
    activity_ValidateAcceptedSubmissionVideos as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


def session_data(filename=None, article_id=None):
    s_data = copy.copy(test_activity_data.accepted_session_example)
    if filename:
        s_data["input_filename"] = filename
    if article_id:
        s_data["article_id"] = article_id
    return s_data


@ddt
class TestValidateAcceptedSubmissionVideos(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())

    @patch("provider.glencoe_check.requests.get")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission with videos and no metadata",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "status_code": 404,
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_deposit_videos_status": True,
        },
        {
            "comment": "accepted submission with videos and already has metadata",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "status_code": 200,
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_deposit_videos_status": False,
        },
        {
            "comment": "accepted submission with videos and an unhandled status code",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "status_code": 500,
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_valid_status": True,
            "expected_deposit_videos_status": None,
        },
        {
            "comment": "accepted submission zip has no videos",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "status_code": 404,
            "expected_xml_file_path": "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "expected_result": True,
            "expected_valid_status": None,
            "expected_deposit_videos_status": None,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_get,
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
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_session.return_value = FakeSession(
            test_activity_data.accepted_session_example
        )
        fake_get.return_value = FakeResponse(test_data.get("status_code"))
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
            self.activity.statuses.get("valid"),
            test_data.get("expected_valid_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("deposit_videos"),
            test_data.get("expected_deposit_videos_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # reset REPAIR_XML value
        activity_module.REPAIR_XML = False

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
        fake_file_list.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "ValidateAcceptedSubmissionVideos, XML ParseError exception "
            "parsing file %s for file %s"
        ) % (xml_file_path, zip_file)
        self.assertEqual(self.activity.logger.logexception, expected_logexception)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(cleaner, "video_data_from_files")
    def test_do_activity_video_data_exception(
        self,
        fake_video_data_from_files,
        fake_email_smtp_connect,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an exception generating video_data_from_files"
        directory = TempDirectory()
        zip_file = "28-09-2020-RA-eLife-63532.zip"
        article_id = zip_file.rsplit("-", 1)[-1].rstrip(".zip")

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
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_video_data_from_files.side_effect = Exception("An exception")
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        # assertions
        expected_logexception = (
            (
                "ValidateAcceptedSubmissionVideos, exception invoking "
                "video_data_from_files() for file %s"
            )
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_logexception)

        expected_email_count = 1
        expected_email_subject = (
            "Error validating videos in accepted submission file: %s" % zip_file
        )
        expected_email_from = "From: sender@example.org"
        expected_email_body_contains = (
            b"Validation messages were generated in the ValidateAcceptedSubmissionVideos "
            b"workflow activity when processing input file %s"
            % bytes(zip_file, encoding="utf-8")
        )
        # check email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)

        # assert number of emails sent
        self.assertEqual(len(email_files), expected_email_count)

        # can look at the first email for the subject and sender
        first_email_content = None
        with open(email_files[0], "r", encoding="utf8") as open_file:
            first_email_content = open_file.read()
        if first_email_content:

            self.assertTrue(expected_email_subject in first_email_content)

            self.assertTrue(expected_email_from in first_email_content)

            body = helpers.body_from_multipart_email_string(first_email_content)
            self.assertTrue(expected_email_body_contains in body)


class TestValidateVideoData(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity_name = "ValidateAcceptedSubmissionVideos"
        self.zip_file = "28-09-2020-RA-eLife-63532.zip"

    def test_validate_video_data_video_id_blank(self):
        "test if there is a blank video_id property in the generated video data"
        generated_video_data = [
            {
                "upload_file_nm": "Video 1 AVI.avi",
                "video_id": None,
                "video_filename": "elife-63532-video1.avi",
            }
        ]
        expected_validation_messages = (
            (
                "ValidateAcceptedSubmissionVideos, %s video file name "
                '"%s" generated a video_id value of %s'
            )
        ) % (
            self.zip_file,
            generated_video_data[0].get("upload_file_nm"),
            generated_video_data[0].get("video_id"),
        )
        # invoke the function
        validation_messages = activity_module.validate_video_data(
            generated_video_data, self.zip_file, self.activity_name, self.logger
        )
        # assertions
        self.assertEqual(validation_messages, expected_validation_messages)
        self.assertEqual(self.logger.loginfo[-1], expected_validation_messages)

    def test_validate_video_data_video_filename_blank(self):
        "test if there is a blank video_filename property in the generated video data"
        generated_video_data = [
            {
                "upload_file_nm": "Video 1 AVI.avi",
                "video_id": "video1",
                "video_filename": None,
            }
        ]
        expected_validation_messages = (
            (
                "ValidateAcceptedSubmissionVideos, %s video file name "
                '"%s" generated a video_filename value of %s'
            )
        ) % (
            self.zip_file,
            generated_video_data[0].get("upload_file_nm"),
            generated_video_data[0].get("video_filename"),
        )

        # invoke the function
        validation_messages = activity_module.validate_video_data(
            generated_video_data, self.zip_file, self.activity_name, self.logger
        )
        # assertions
        self.assertEqual(validation_messages, expected_validation_messages)
        self.assertEqual(self.logger.loginfo[-1], expected_validation_messages)

    def test_validate_video_data_duplicates(self):
        "test if there is a duplicate video_id or video_filename"
        generated_video_data = [
            {
                "upload_file_nm": "Video 1 AVI.avi",
                "video_id": "video1",
                "video_filename": "elife-63532-video1.avi",
            },
            {
                "upload_file_nm": "Video 1b AVI.avi",
                "video_id": "video1",
                "video_filename": "elife-63532-video1.avi",
            },
        ]
        expected_validation_messages = (
            "ValidateAcceptedSubmissionVideos, %s duplicate video_id or video_filename generated"
        ) % (self.zip_file,)

        # invoke the function
        validation_messages = activity_module.validate_video_data(
            generated_video_data, self.zip_file, self.activity_name, self.logger
        )
        # assertions
        self.assertEqual(validation_messages, expected_validation_messages)
        self.assertEqual(self.logger.loginfo[-1], expected_validation_messages)


class TestErrorEmailSubject(unittest.TestCase):
    def test_error_email_subject(self):
        "email subject line with correct output_file value"

        class continuumtest:
            "mock settings object for testing"
            pass

        output_file = "file.zip"
        expected = (
            "TEST Error validating videos in accepted submission file: %s" % output_file
        )
        subject = activity_module.error_email_subject(output_file, continuumtest)
        self.assertEqual(subject, expected)

    def test_no_settings_class_name(self):
        "test if the settings is not a class"
        output_file = "file.zip"
        expected = (
            "Error validating videos in accepted submission file: %s" % output_file
        )
        subject = activity_module.error_email_subject(output_file, settings_mock)
        self.assertEqual(subject, expected)

    def test_settings_none(self):
        "test if settings is not passed as an argument"
        output_file = "file.zip"
        expected = (
            "Error validating videos in accepted submission file: %s" % output_file
        )
        subject = activity_module.error_email_subject(output_file)
        self.assertEqual(subject, expected)
