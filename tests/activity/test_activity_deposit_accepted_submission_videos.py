# coding=utf-8

import os
import glob
import copy
import shutil
import unittest
import zipfile
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_DepositAcceptedSubmissionVideos as activity_module
from activity.activity_DepositAcceptedSubmissionVideos import (
    activity_DepositAcceptedSubmissionVideos as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeFTP,
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = copy.copy(test_case_data.ingest_accepted_submission_data)
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


def expanded_folder_renamed_video_resources(directory, expanded_folder, zip_file_path):
    "populate the expanded folder with files and rename and modify them to match expected data"
    resources = helpers.expanded_folder_bucket_resources(
        directory, expanded_folder, zip_file_path
    )
    if zip_file_path.rsplit("/", 1)[-1] == "28-09-2020-RA-eLife-63532.zip":
        sub_folder = "28-09-2020-RA-eLife-63532"
        video_file_map = {
            "Video 1 AVI.avi": "elife-63532-video1.avi",
            "Video 2 AVI .avi": "elife-63532-video2.avi",
        }
        xml_file = "28-09-2020-RA-eLife-63532.xml"
        xml_file_path = os.path.join(
            directory.path, expanded_folder, sub_folder, xml_file
        )
        # read the XML file content
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for from_file, to_file in video_file_map.items():
            # rename the file on disk
            shutil.move(
                os.path.join(directory.path, expanded_folder, sub_folder, from_file),
                os.path.join(directory.path, expanded_folder, sub_folder, to_file),
            )
            # replace in the XML content
            xml_content = xml_content.replace(from_file, to_file)
            # alter the resources list items
            resources.remove("%s/%s" % (sub_folder, from_file))
            resources.append("%s/%s" % (sub_folder, to_file))
        # write the final XML out to the file
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_content)
    return resources


@ddt
class TestDepositAcceptedSubmissionVideos(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission with videos",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "article_id": "63532",
            "deposit_videos": True,
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_generate_status": True,
            "expected_zip_status": True,
            "expected_deposit_status": True,
            "expected_file_count": 26,
            "expected_zip_file_name": "elife_videos_28-09-2020-RA-eLife-63532.zip",
            "expected_zip_file_list": [
                "elife-63532-video1.avi",
                "elife-63532-video2.avi",
                "elife_videos_28-09-2020-RA-eLife-63532.xml",
            ],
        },
        {
            "comment": "accepted submission zip has no videos",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "article_id": "45644",
            "deposit_videos": None,
            "expected_xml_file_path": None,
            "expected_result": True,
            "expected_generate_status": None,
            "expected_zip_status": None,
            "expected_deposit_status": None,
            "expected_file_count": 42,
            "expected_zip_file_name": None,
            "expected_zip_file_list": [],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_ftp,
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
        resources = expanded_folder_renamed_video_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        workflow_session_data = session_data(
            filename=test_data.get("filename"),
            article_id=test_data.get("article_id"),
            deposit_videos=test_data.get("deposit_videos"),
        )
        fake_ftp.return_value = FakeFTP()
        fake_session.return_value = FakeSession(workflow_session_data)
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        input_dir_files = glob.glob(self.activity.directories.get("INPUT_DIR") + "/*/*")

        if test_data.get("expected_xml_file_path"):
            xml_file_path = os.path.join(
                self.activity.directories.get("INPUT_DIR"),
                test_data.get("expected_xml_file_path"),
            )
            self.assertTrue(xml_file_path in input_dir_files)

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
            self.activity.statuses.get("generate"),
            test_data.get("expected_generate_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("zip"),
            test_data.get("expected_zip_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("deposit"),
            test_data.get("expected_deposit_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # assert the video zip file was created
        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*")
        if test_data.get("expected_zip_file_name"):
            video_zip_file_path = os.path.join(
                self.activity.directories.get("TEMP_DIR"),
                test_data.get("expected_zip_file_name"),
            )
            self.assertTrue(
                video_zip_file_path in temp_dir_files,
                "zip not found in temp dir files %s" % temp_dir_files,
            )
            # assert the contents of the video zip file
            if test_data.get("expected_zip_file_list"):
                with zipfile.ZipFile(video_zip_file_path, "r") as open_zip:
                    zip_namelist = open_zip.namelist()
                    self.assertEqual(
                        sorted(zip_namelist),
                        sorted(test_data.get("expected_zip_file_list")),
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
            self.activity.directories.get("INPUT_DIR"),
            xml_file,
        )

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, deposit_videos=True)
        )
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_file,
        )
        resources = expanded_folder_renamed_video_resources(
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
            "DepositAcceptedSubmissionVideos, XML ParseError exception "
            "parsing video file list from %s for file %s"
        ) % (xml_file_path, zip_file)
        self.assertEqual(self.activity.logger.logexception, expected_logexception)


class TestDepositAcceptedSubmissionVideosFtpExceptions(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        filename = "28-09-2020-RA-eLife-63532.zip"
        article_id = "63532"
        # expanded bucket files
        self.directory = TempDirectory()
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            filename,
        )
        self.resources = expanded_folder_renamed_video_resources(
            self.directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )
        self.workflow_session_data = session_data(
            filename=filename,
            article_id=article_id,
            deposit_videos=True,
        )
        self.input_data = input_data(filename)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "storage_context")
    @patch.object(FakeFTP, "ftp_connect")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_ftp_connect_exception(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_ftp,
        fake_ftp_connect,
        fake_storage_context,
    ):
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_ftp.return_value = FakeFTP()
        fake_ftp_connect.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch.object(FakeFTP, "ftp_to_endpoint")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_ftp_to_endpoint_exception(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_ftp,
        fake_ftp_to_endpoint,
        fake_storage_context,
    ):
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_ftp.return_value = FakeFTP()
        fake_ftp_to_endpoint.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch.object(FakeFTP, "ftp_disconnect")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_ftp_disconnect_exception(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_ftp,
        fake_ftp_disconnect,
        fake_storage_context,
    ):
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_ftp.return_value = FakeFTP()
        fake_ftp_disconnect.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch.object(FakeFTP, "ftp_disconnect")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_ftp_exception_increment_attempts(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_ftp,
        fake_ftp_disconnect,
        fake_storage_context,
    ):
        "test if session variable count of attempts already exists"
        self.workflow_session_data[activity_module.SESSION_ATTEMPT_COUNTER_NAME] = 1
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_ftp.return_value = FakeFTP()
        fake_ftp_disconnect.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch.object(FakeFTP, "ftp_disconnect")
    @patch.object(activity_module, "FTP")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_ftp_exception_max_attempts(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_ftp,
        fake_ftp_disconnect,
        fake_storage_context,
    ):
        "test if attempt count exceeds the max attempts"
        self.workflow_session_data[
            activity_module.SESSION_ATTEMPT_COUNTER_NAME
        ] = 1000000
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_ftp.return_value = FakeFTP()
        fake_ftp_disconnect.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, True)


class TestDepositVideosDepositVideosNone(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch.object(activity_module, "get_session")
    def test_do_activity_deposit_videos_none(
        self,
        fake_session,
    ):
        "test if there is no deposit_videos value in the session"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(session_data(zip_file, article_id))
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_loginfo = (
            "DepositAcceptedSubmissionVideos, %s"
            " deposit_videos session value is None, activity returning True"
        ) % zip_file
        self.assertEqual(self.activity.logger.loginfo[-1], expected_loginfo)


class TestDepositVideosNoCredentials(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # change settings value
        self.glencoe_ftp_uri = self.activity.settings.GLENCOE_FTP_URI
        del self.activity.settings.GLENCOE_FTP_URI

    def tearDown(self):
        # restore settings value
        self.activity.settings.GLENCOE_FTP_URI = self.glencoe_ftp_uri

    @patch.object(activity_module, "get_session")
    def test_do_activity_deposit_videos_no_credentials(
        self,
        fake_session,
    ):
        "test if there are no credentials in the settings"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base
        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, True)
        )
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_exception_message = (
            "DepositAcceptedSubmissionVideos, %s"
            " settings credential GLENCOE_FTP_URI is missing"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_exception_message)


class TestDepositVideosBlankCredentials(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # change settings value
        self.glencoe_ftp_uri = self.activity.settings.GLENCOE_FTP_URI
        self.activity.settings.GLENCOE_FTP_URI = ""

    def tearDown(self):
        # restore settings value
        self.activity.settings.GLENCOE_FTP_URI = self.glencoe_ftp_uri

    @patch.object(activity_module, "get_session")
    def test_do_activity_deposit_videos_blank_credentials(
        self,
        fake_session,
    ):
        "test if there are blank credentials in the settings"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, True)
        )
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_exception_message = (
            "DepositAcceptedSubmissionVideos, %s"
            " settings credential GLENCOE_FTP_URI is blank"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_exception_message)
