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
import activity.activity_AcceptedSubmissionPeerReviewImages as activity_module
from activity.activity_AcceptedSubmissionPeerReviewImages import (
    activity_AcceptedSubmissionPeerReviewImages as activity_object,
)
import tests.test_data as test_case_data
from tests.classes_mock import FakeSMTPServer
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
class TestAcceptedSubmissionPeerReviewImages(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(
            copy.copy(test_activity_data.accepted_session_example)
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch("requests.get")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": None,
            "expected_external_hrefs_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewImages, no inline-graphic tags in "
                    "30-01-2019-RA-eLife-45644.zip"
                )
            ],
        },
        {
            "comment": "example with a non-external inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="local.jpg" />'
                "</sub-article>"
            ),
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewImages, no inline-graphic tags with "
                    "external href values in 30-01-2019-RA-eLife-45644.zip"
                )
            ],
        },
        {
            "comment": "example with an external inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="local.jpg" />'
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                '<inline-graphic xlink:href="https://i.imgur.com/FFeuydR.jpg" />'
                "</sub-article>"
            ),
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewImages, downloaded href "
                    "https://i.imgur.com/vc4GR10.png to"
                )
            ],
            "expected_xml_contains": [
                (
                    '<file file-type="figure">'
                    "<upload_file_nm>elife-45644-inf1.png</upload_file_nm>"
                    "</file>"
                    '<file file-type="figure">'
                    "<upload_file_nm>elife-45644-inf2.jpg</upload_file_nm>"
                    "</file></files>"
                ),
                (
                    '<inline-graphic xlink:href="elife-45644-inf1.png"/>'
                    '<inline-graphic xlink:href="elife-45644-inf2.jpg"/>'
                ),
            ],
        },
        {
            "comment": "example with unapproved inline-graphic values",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="local.jpg" />'
                '<inline-graphic xlink:href="https://example.org/fake.jpg" />'
                '<inline-graphic xlink:href="https://example.org/no_zip_please.zip" />'
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                "</sub-article>"
            ),
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_cleaner_log_contains": [
                (
                    "https://example.org/fake.jpg peer review image href "
                    "was not approved for downloading"
                ),
            ],
        },
        {
            "comment": "example with duplicate inline-graphic values",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                "</sub-article>"
            ),
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_bucket_upload_folder_contents": [
                "30-01-2019-RA-eLife-45644.xml",
                "elife-45644-inf1.png",
            ],
            "expected_xml_contains": [
                (
                    '<file file-type="figure">'
                    "<upload_file_nm>elife-45644-inf1.png</upload_file_nm>"
                    "</file></files>"
                ),
                (
                    '<inline-graphic xlink:href="elife-45644-inf1.png"/>'
                    '<inline-graphic xlink:href="elife-45644-inf1.png"/>'
                ),
            ],
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewImages, href https://i.imgur.com/vc4GR10.png "
                    "was already downloaded"
                )
            ],
        },
        {
            "comment": "example with get request non-200 status code",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                "</sub-article>"
            ),
            "status_code": 404,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": None,
            "expected_bucket_upload_folder_contents": [],
            "expected_activity_log_contains": [
                "GET request returned a 404 status code for https://i.imgur.com/vc4GR10.png",
                (
                    "AcceptedSubmissionPeerReviewImages, href https://i.imgur.com/vc4GR10.png "
                    "could not be downloaded"
                ),
            ],
            "expected_cleaner_log_contains": [
                (
                    "https://i.imgur.com/vc4GR10.png peer review image href "
                    "was not downloaded successfully"
                ),
            ],
            "expected_email_count": 1,
            "expected_email_subject": (
                "Error in accepted submission peer review images: "
                "30-01-2019-RA-eLife-45644.zip"
            ),
            "expected_email_from": "From: sender@example.org",
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
        fake_email_smtp_connect,
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

        # write additional XML to the XML file
        if test_data.get("sub_article_xml"):
            xml_filename = "%s.xml" % test_data.get("filename").rsplit(".", 1)[0]
            xml_path = helpers.expanded_article_xml_path(
                xml_filename,
                directory.path,
                self.session.get_value("expanded_folder"),
            )
            helpers.add_sub_article_xml(
                xml_path,
                test_data.get("sub_article_xml"),
            )

        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session

        fake_response = FakeResponse(test_data.get("status_code"))
        # an image file to test with
        with open(
            "tests/files_source/digests/outbox/99999/digest-99999.jpg", "rb"
        ) as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        # assertion on XML contents
        if test_data.get("expected_xml_contains"):
            with open(xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains"):
                self.assertTrue(fragment in xml_content)

        self.assertEqual(
            self.activity.statuses.get("hrefs"),
            test_data.get("expected_hrefs_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("external_hrefs"),
            test_data.get("expected_external_hrefs_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on cleaner.log contents
        if test_data.get("expected_cleaner_log_contains"):
            log_file_path = os.path.join(
                self.activity.get_tmp_dir(), self.activity.activity_log_file
            )
            with open(log_file_path, "r", encoding="utf8") as open_file:
                log_contents = open_file.read()
            for fragment in test_data.get("expected_cleaner_log_contains"):
                self.assertTrue(
                    fragment in log_contents,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on the session cleaner log content
        if test_data.get("expected_upload_xml_status"):
            session_log = self.session.get_value("cleaner_log")
            self.assertIsNotNone(
                session_log,
                "failed in {comment}".format(comment=test_data.get("comment")),
            )

        # check output bucket folder contents
        if "expected_bucket_upload_folder_contents" in test_data:
            bucket_folder_path = os.path.join(
                dest_folder,
                test_activity_data.accepted_session_example.get("expanded_folder"),
                "30-01-2019-RA-eLife-45644",
            )
            try:
                output_bucket_list = os.listdir(bucket_folder_path)
            except FileNotFoundError:
                # no objects were uploaded so the folder path does not exist
                output_bucket_list = []
            self.assertEqual(
                sorted(output_bucket_list),
                sorted(test_data.get("expected_bucket_upload_folder_contents")),
            )

        # check assertions on email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0], encoding="utf-8") as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(
                        test_data.get("expected_email_subject") in first_email_content
                    )
                if test_data.get("expected_email_from"):
                    self.assertTrue(
                        test_data.get("expected_email_from") in first_email_content
                    )
