# coding=utf-8

import copy
import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner, github_provider
import activity.activity_MecaPeerReviewImages as activity_module
from activity.activity_MecaPeerReviewImages import (
    activity_MecaPeerReviewImages as activity_object,
)
from tests import list_files
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data

SESSION_DICT = test_activity_data.ingest_meca_session_example()


@ddt
class TestMecaPeerReviewImages(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))
        # save original constant value
        self.fail_if_no_images_downloaded = activity_module.FAIL_IF_NO_IMAGES_DOWNLOADED

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset constant to original value
        activity_module.FAIL_IF_NO_IMAGES_DOWNLOADED = self.fail_if_no_images_downloaded

    @patch.object(github_provider, "find_github_issue")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch("requests.get")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no inline-graphic",
            "status_code": 200,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": None,
            "expected_external_hrefs_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "MecaPeerReviewImages, no inline-graphic tags in "
                    "10.7554/eLife.95901.1"
                )
            ],
        },
        {
            "comment": "example with a non-external inline-graphic",
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
                    "MecaPeerReviewImages, no inline-graphic tags with "
                    "external href values in 10.7554/eLife.95901.1"
                )
            ],
            "expected_session_log_contains": [],
        },
        {
            "comment": "example with an external inline-graphic",
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
                    "MecaPeerReviewImages, downloaded href "
                    "https://i.imgur.com/vc4GR10.png to"
                )
            ],
            "expected_xml_contains": [
                (
                    '<inline-graphic xlink:href="elife-95901-inf1.png"/>'
                    '<inline-graphic xlink:href="elife-95901-inf2.jpg"/>'
                ),
            ],
            "expected_manifest_xml_contains": [
                (
                    '<item id="inf1" type="figure">'
                    '<instance href="content/elife-95901-inf1.png" media-type="image/png"/>'
                    "</item>"
                    '<item id="inf2" type="figure">'
                    '<instance href="content/elife-95901-inf2.jpg" media-type="image/jpeg"/>'
                    "</item>"
                ),
            ],
            "expected_session_log_contains": [],
            "expected_cleaner_log_contains": [
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file "
                ),
                "/tmp_dir/manifest.xml",
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file"
                ),
                "/tmp_dir/content/24301711.xml",
            ],
        },
        {
            "comment": "example with unapproved inline-graphic values",
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
            "expected_session_log_contains": [
                (
                    "https://example.org/fake.jpg peer review image href"
                    " was not approved for downloading"
                ),
                (
                    "https://example.org/no_zip_please.zip peer review image href"
                    " was not approved for downloading"
                ),
            ],
            "expected_cleaner_log_contains": [
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file "
                ),
                "/tmp_dir/manifest.xml",
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file"
                ),
                "/tmp_dir/content/24301711.xml",
            ],
        },
        {
            "comment": "example with duplicate inline-graphic values",
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
                "manifest.xml",
                "content/24301711.xml",
                "content/elife-95901-inf1.png",
            ],
            "expected_xml_contains": [
                (
                    '<inline-graphic xlink:href="elife-95901-inf1.png"/>'
                    '<inline-graphic xlink:href="elife-95901-inf1.png"/>'
                ),
            ],
            "expected_manifest_xml_contains": [
                (
                    '<item id="inf1" type="figure">'
                    '<instance href="content/elife-95901-inf1.png" media-type="image/png"/>'
                    "</item>"
                ),
            ],
            "expected_activity_log_contains": [
                (
                    "MecaPeerReviewImages, href https://i.imgur.com/vc4GR10.png "
                    "was already downloaded"
                )
            ],
            "expected_session_log_contains": [],
            "expected_cleaner_log_contains": [
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file "
                ),
                "/tmp_dir/manifest.xml",
                (
                    "INFO elifecleaner:transform:write_xml_file:"
                    " 10.7554/eLife.95901.1 writing xml to file"
                ),
                "/tmp_dir/content/24301711.xml",
            ],
        },
        {
            "comment": "example with get request non-200 status code and do not fail workflow",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                "</sub-article>"
            ),
            "status_code": 404,
            "fail_if_no_images_downloaded": False,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": None,
            "expected_bucket_upload_folder_contents": [],
            "expected_activity_log_contains": [
                "GET request returned a 404 status code for https://i.imgur.com/vc4GR10.png",
                (
                    "MecaPeerReviewImages, href https://i.imgur.com/vc4GR10.png "
                    "could not be downloaded"
                ),
            ],
            "expected_session_log_contains": [
                (
                    "MecaPeerReviewImages, peer review image https://i.imgur.com/vc4GR10.png"
                    " was not downloaded successfully for 10.7554/eLife.95901.1"
                )
            ],
        },
        {
            "comment": "example non-200 status code and fail workflow based on constant value",
            "sub_article_xml": (
                "<sub-article>"
                '<inline-graphic xlink:href="https://i.imgur.com/vc4GR10.png" />'
                "</sub-article>"
            ),
            "status_code": 404,
            "fail_if_no_images_downloaded": True,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_external_hrefs_status": True,
            "expected_upload_xml_status": None,
            "expected_bucket_upload_folder_contents": [],
            "expected_activity_log_contains": [
                "GET request returned a 404 status code for https://i.imgur.com/vc4GR10.png",
                (
                    "MecaPeerReviewImages, href https://i.imgur.com/vc4GR10.png "
                    "could not be downloaded"
                ),
            ],
            "expected_session_log_contains": [
                (
                    "MecaPeerReviewImages, peer review image https://i.imgur.com/vc4GR10.png"
                    " was not downloaded successfully for 10.7554/eLife.95901.1"
                )
            ],
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
        fake_find_github_issue,
    ):
        directory = TempDirectory()
        fake_find_github_issue.return_value = FakeGithubIssue()
        fake_clean_tmp_dir.return_value = None
        fake_session.return_value = self.session

        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data, directory.path
        )

        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )

        fake_response = FakeResponse(test_data.get("status_code"))
        # an image file to test with
        with open(
            "tests/files_source/digests/outbox/99999/digest-99999.jpg", "rb"
        ) as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        # set constant
        if test_data.get("fail_if_no_images_downloaded"):
            activity_module.FAIL_IF_NO_IMAGES_DOWNLOADED = test_data.get(
                "fail_if_no_images_downloaded"
            )

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # assert
        temp_dir_files = list_files(self.activity.directories.get("TEMP_DIR"))

        self.assertTrue(populated_data.get("xml_file_name") in temp_dir_files)

        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("xml_file_name"),
        )

        # assertion on XML contents
        if test_data.get("expected_xml_contains"):
            with open(xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains"):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        self.assertTrue(populated_data.get("manifest_file_name") in temp_dir_files)

        manifest_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        if test_data.get("expected_manifest_xml_contains"):
            with open(manifest_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_manifest_xml_contains"):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

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

        # assertion on session log content
        if test_data.get("expected_session_log_contains"):
            for fragment in test_data.get("expected_session_log_contains"):
                self.assertTrue(
                    fragment in str(self.session.get_value("log_messages")),
                    "failed in {comment}, did not find fragment {fragment}".format(
                        comment=test_data.get("comment"), fragment=fragment
                    ),
                )

        # assertion on cleaner log contents
        if test_data.get("expected_cleaner_log_contains"):
            for fragment in test_data.get("expected_cleaner_log_contains"):
                self.assertTrue(
                    fragment in str(self.session.get_value("cleaner_log")),
                    "failed in {comment}, did not find fragment {fragment}".format(
                        comment=test_data.get("comment"), fragment=fragment
                    ),
                )

        # check output bucket folder contents
        if "expected_bucket_upload_folder_contents" in test_data:
            bucket_files = list_files(
                os.path.join(
                    dest_folder,
                    self.session.get_value("expanded_folder"),
                )
            )
            if test_data.get("expected_bucket_upload_folder_contents"):
                self.assertEqual(
                    sorted(bucket_files),
                    sorted(test_data.get("expected_bucket_upload_folder_contents")),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )
            else:
                # test helper returns None if the folder path does not exist
                self.assertEqual(bucket_files, None)
