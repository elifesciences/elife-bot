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
from provider import cleaner, glencoe_check
import activity.activity_AnnotateAcceptedSubmissionVideos as activity_module
from activity.activity_AnnotateAcceptedSubmissionVideos import (
    activity_AnnotateAcceptedSubmissionVideos as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


GLENCOE_METADATA_ARTICLE_63532 = {
    "video1": {
        "source_href": (
            "https://static-movie-usa.glencoesoftware.com/source/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.avi"
        ),
        "doi": "",
        "flv_href": (
            "https://static-movie-usa.glencoesoftware.com/flv/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.flv"
        ),
        "uuid": "6a2538e3-621a-4412-b037-bbb7db4bec36",
        "title": "video1",
        "video_id": "video1",
        "solo_href": "https://movie-usa.glencoesoftware.com/video/10.7554/eLife.63532/video1",
        "height": 473,
        "ogv_href": (
            "https://static-movie-usa.glencoesoftware.com/ogv/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.ogv"
        ),
        "width": 473,
        "legend": "",
        "href": "elife-63532-video1.avi",
        "webm_href": (
            "https://static-movie-usa.glencoesoftware.com/webm/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.webm"
        ),
        "jpg_href": (
            "https://static-movie-usa.glencoesoftware.com/jpg/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.jpg"
        ),
        "duration": 8.714286,
        "mp4_href": (
            "https://static-movie-usa.glencoesoftware.com/mp4/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.mp4"
        ),
        "id": "",
        "size": 40976840,
    },
    "video2": {
        "source_href": (
            "https://static-movie-usa.glencoesoftware.com/source/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.avi"
        ),
        "doi": "",
        "flv_href": (
            "https://static-movie-usa.glencoesoftware.com/flv/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.flv"
        ),
        "uuid": "86a0d2c8-d6f2-4aa8-b07f-4c089d0f5423",
        "title": "video2",
        "video_id": "video2",
        "solo_href": "https://movie-usa.glencoesoftware.com/video/10.7554/eLife.63532/video2",
        "height": 346,
        "ogv_href": (
            "https://static-movie-usa.glencoesoftware.com/ogv/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.ogv"
        ),
        "width": 502,
        "legend": "",
        "href": "elife-63532-video2.avi",
        "webm_href": (
            "https://static-movie-usa.glencoesoftware.com/webm/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.webm"
        ),
        "jpg_href": (
            "https://static-movie-usa.glencoesoftware.com/jpg/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.jpg"
        ),
        "duration": 4.428571,
        "mp4_href": (
            "https://static-movie-usa.glencoesoftware.com/mp4/10.7554/202/"
            "c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.mp4"
        ),
        "id": "",
        "size": 520732,
    },
}


def input_data(file_name_to_change=""):
    activity_data = copy.copy(test_case_data.ingest_accepted_submission_data)
    activity_data["file_name"] = file_name_to_change
    return activity_data


def session_data(
    filename=None, article_id=None, deposit_videos=None, annotate_videos=None
):
    s_data = copy.copy(test_activity_data.accepted_session_example)
    if filename:
        s_data["input_filename"] = filename
    if article_id:
        s_data["article_id"] = article_id
    if deposit_videos:
        s_data["deposit_videos"] = deposit_videos
    if annotate_videos:
        s_data["annotate_videos"] = annotate_videos
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
class TestAnnotateAcceptedSubmissionVideos(unittest.TestCase):
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
    @patch("requests.get")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "accepted submission with videos",
            "filename": "28-09-2020-RA-eLife-63532.zip",
            "article_id": "63532",
            "annotate_videos": True,
            "expected_xml_file_path": "28-09-2020-RA-eLife-63532/28-09-2020-RA-eLife-63532.xml",
            "expected_result": True,
            "expected_get_status": True,
            "expected_annotate_status": True,
            "expected_upload_xml_status": True,
            "expected_xml": [
                '<file file-type="video" glencoe-jpg="https://static-movie-usa.glencoesoftware.com/jpg/10.7554/202/c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.jpg" glencoe-mp4="https://static-movie-usa.glencoesoftware.com/mp4/10.7554/202/c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video1.mp4" id="video1">',
                '<file file-type="video" glencoe-jpg="https://static-movie-usa.glencoesoftware.com/jpg/10.7554/202/c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.jpg" glencoe-mp4="https://static-movie-usa.glencoesoftware.com/mp4/10.7554/202/c0f4d0de3cd6bcc603bf3ef7a9435a8475709023/elife-63532-video2.mp4" id="video2">',
            ],
        },
        {
            "comment": "accepted submission zip has no videos",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "article_id": "45644",
            "annotate_videos": None,
            "expected_xml_file_path": None,
            "expected_result": True,
            "expected_get_status": None,
            "expected_annotate_status": None,
            "expected_upload_xml_status": None,
            "expected_xml": [],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_get,
        fake_cleaner_storage_context,
        fake_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        # video get metadata response
        fake_get.return_value = FakeResponse(200, GLENCOE_METADATA_ARTICLE_63532)

        workflow_session_data = session_data(
            filename=test_data.get("filename"),
            article_id=test_data.get("article_id"),
            annotate_videos=test_data.get("annotate_videos"),
        )
        fake_session.return_value = FakeSession(workflow_session_data)

        # expanded bucket files
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            test_data.get("filename"),
        )
        resources = expanded_folder_renamed_video_resources(
            directory,
            workflow_session_data.get("expanded_folder"),
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
            self.activity.statuses.get("get"),
            test_data.get("expected_get_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("annotate"),
            test_data.get("expected_annotate_status"),
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

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch("requests.get")
    @patch.object(cleaner, "parse_article_xml")
    def test_do_activity_exception_parseerror(
        self,
        fake_parse_article_xml,
        fake_get,
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
        # video get metadata response
        fake_get.return_value = FakeResponse(200, None)
        fake_session.return_value = FakeSession(
            session_data(
                zip_file, article_id, deposit_videos=True, annotate_videos=True
            )
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
        fake_parse_article_xml.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "AnnotateAcceptedSubmissionVideos, XML ParseError exception "
            "parsing XML %s for file %s"
        ) % (xml_file_path, zip_file)
        self.assertEqual(self.activity.logger.logexception, expected_logexception)


class TestAnnotateAcceptedSubmissionVideosGlencoeExceptions(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        filename = "28-09-2020-RA-eLife-63532.zip"
        article_id = "63532"
        # expanded bucket files
        self.directory = TempDirectory()

        self.workflow_session_data = session_data(
            filename=filename,
            article_id=article_id,
            annotate_videos=True,
        )

        # expanded bucket files
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            filename,
        )
        self.resources = expanded_folder_renamed_video_resources(
            self.directory,
            self.workflow_session_data.get("expanded_folder"),
            zip_file_path,
        )
        self.dest_folder = os.path.join(
            self.directory.path, self.workflow_session_data.get("expanded_folder")
        )
        self.input_data = input_data(filename)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "storage_context")
    @patch.object(glencoe_check, "metadata")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_metadata_exception(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_metadata,
        fake_storage_context,
    ):
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_metadata.side_effect = Exception("An exception")
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch("requests.get")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_metadata_404(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_get,
        fake_storage_context,
    ):
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            self.directory.path, self.resources
        )
        fake_session.return_value = FakeSession(self.workflow_session_data)
        fake_get.return_value = FakeResponse(404, None)
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch("requests.get")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_metadata_404_increment_attempts(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_get,
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
        fake_get.return_value = FakeResponse(404, None)
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, "ActivityTemporaryFailure")

    @patch.object(activity_module, "storage_context")
    @patch("requests.get")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_metadata_404_max_attempts(
        self,
        fake_session,
        fake_cleaner_storage_context,
        fake_get,
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
        fake_get.return_value = FakeResponse(404, None)
        result = self.activity.do_activity(self.input_data)
        self.assertEqual(result, True)


class TestAnnotateVideosAnnotateVideosNone(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    @patch.object(activity_module, "get_session")
    def test_do_activity_annotate_videos_none(
        self,
        fake_session,
    ):
        "test if there is no annotate_videos value in the session"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(session_data(zip_file, article_id))
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_loginfo = (
            "AnnotateAcceptedSubmissionVideos, %s"
            " annotate_videos session value is None, activity returning True"
        ) % zip_file
        self.assertEqual(self.activity.logger.loginfo[-1], expected_loginfo)


class TestAnnotateVideosNoCredentials(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # change settings value
        self.video_url = self.activity.settings.video_url
        del self.activity.settings.video_url

    def tearDown(self):
        # restore settings value
        self.activity.settings.video_url = self.video_url

    @patch.object(activity_module, "get_session")
    def test_do_activity_annotate_videos_no_credentials(
        self,
        fake_session,
    ):
        "test if there are no credentials in the settings"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base
        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, True, True)
        )
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_exception_message = (
            "AnnotateAcceptedSubmissionVideos, %s"
            " settings credential video_url is missing"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_exception_message)


class TestAnnotateVideosBlankCredentials(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # change settings value
        self.video_url = self.activity.settings.video_url
        self.activity.settings.video_url = ""

    def tearDown(self):
        # restore settings value
        self.activity.settings.video_url = self.video_url

    @patch.object(activity_module, "get_session")
    def test_do_activity_annotate_videos_blank_credentials(
        self,
        fake_session,
    ):
        "test if there are blank credentials in the settings"
        zip_file_base = "28-09-2020-RA-eLife-63532"
        article_id = zip_file_base.rsplit("-", 1)[-1]
        zip_file = "%s.zip" % zip_file_base

        fake_session.return_value = FakeSession(
            session_data(zip_file, article_id, True, True)
        )
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_exception_message = (
            "AnnotateAcceptedSubmissionVideos, %s"
            " settings credential video_url is blank"
        ) % zip_file
        self.assertEqual(self.activity.logger.logexception, expected_exception_message)
