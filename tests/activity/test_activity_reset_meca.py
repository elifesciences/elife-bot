# coding=utf-8

import copy
import os
import glob
import shutil
import unittest
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner, github_provider
import activity.activity_ResetMeca as activity_module
from activity.activity_ResetMeca import (
    activity_ResetMeca as activity_object,
)
from tests import list_files
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


@ddt
class TestResetMeca(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)

    @patch.object(github_provider, "find_github_issue")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no sub-article XML",
            "image_names": None,
            "expected_result": True,
            "expected_sub_article_status": False,
            "expected_modify_xml_status": None,
            "expected_modify_manifest_xml_status": None,
            "expected_modify_files_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                ("ResetMeca, no sub-article XML in 10.7554/eLife.95901.1")
            ],
            "expected_xml_not_contains": [
                "<sub-article",
            ],
        },
        {
            "comment": "example with sub-article XML and peer review images",
            "sub_article_xml": (
                '<sub-article id="sa0">'
                "<body>"
                '<p><inline-graphic xlink:href="elife-99548-inf1.jpg"/></p>'
                '<p><inline-graphic xlink:href="elife-99548-inf2.jpg"/></p>'
                '<p><ext-link ext-link-type="uri" xlink:href="https://imgur.com/QM79SPF">'
                '<inline-graphic xlink:href="https://i.imgur.com/QM79SPF.jpg"'
                ' mimetype="image" mime-subtype="jpeg"/></ext-link>'
                "</p>"
                "</body>"
                "</sub-article>"
                '<sub-article id="sa1">'
                "<body>"
                '<fig id="sa1fig1">'
                "<label>Author response image 1.</label>"
                '<graphic mime-subtype="jpg"'
                ' xlink:href="elife-99548-sa1-fig1.jpg" mimetype="image"/>'
                "</fig>"
                "</body>"
                "</sub-article>"
            ),
            "image_names": [
                "elife-99548-inf1.jpg",
                "elife-99548-inf2.jpg",
                "elife-99548-sa1-fig1.jpg",
            ],
            "expected_result": True,
            "expected_sub_article_status": True,
            "expected_modify_xml_status": True,
            "expected_modify_manifest_xml_status": True,
            "expected_modify_files_status": True,
            "expected_upload_xml_status": True,
            "expected_xml_contains": [
                ('<graphic xlink:href="24301711v1_fig1.tif"/>'),
            ],
            "expected_xml_not_contains": [
                ("<sub-article"),
            ],
            "expected_bucket_upload_folder_contents": [
                "content/24301711.xml",
                "manifest.xml",
            ],
            "expected_bucket_folder_not_contents": [
                "content/elife-99548-inf1.jpg",
                "content/elife-99548-inf2.jpg",
                "content/elife-99548-sa1-fig1.jpg",
            ],
            "expected_manifest_xml_contains": [
                (
                    '<instance media-type="image/tiff" href="content/24301711v1_fig1.tif"/>'
                ),
            ],
            "expected_manifest_xml_not_contains": [
                '<instance href="content/elife-99548-inf1.jpg" media-type="image/jpeg"/>',
                '<instance href="content/elife-99548-inf2.jpg" media-type="image/jpeg"/>',
                '<instance href="content/elife-99548-sa1-fig1.jpg" media-type="image/jpeg"/>',
            ],
            "expected_activity_log_contains": [
                "ResetMeca, found 1 graphic in sub-article XML in 10.7554/eLife.95901.1",
                "ResetMeca, found 3 inline-graphic in sub-article XML in 10.7554/eLife.95901.1",
                (
                    "ResetMeca, ignoring https://i.imgur.com/QM79SPF.jpg from image file"
                    " removal list in 10.7554/eLife.95901.1"
                ),
            ],
            "expected_cleaner_log_contains": [
                "10.7554/eLife.95901.1 writing xml to file tmp/"
            ],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
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

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, test_data.get("expected_result"))

        # check output bucket folder contents
        if "expected_bucket_upload_folder_contents" in test_data:
            bucket_folder_path = os.path.join(
                dest_folder, SESSION_DICT.get("expanded_folder")
            )
            output_bucket_list = list_files(bucket_folder_path)
            for bucket_file in test_data.get("expected_bucket_upload_folder_contents"):
                self.assertTrue(
                    bucket_file in output_bucket_list,
                    "%s not found in bucket upload folder" % bucket_file,
                )

        # assert files are missing from the bucket expanded folder
        if "expected_bucket_folder_not_contents" in test_data:
            bucket_folder_path = os.path.join(
                directory.path, SESSION_DICT.get("expanded_folder")
            )
            output_bucket_list = list_files(bucket_folder_path)
            for bucket_file in test_data.get("expected_bucket_folder_not_contents"):
                self.assertTrue(
                    bucket_file not in output_bucket_list,
                    "%s not found in bucket upload folder" % bucket_file,
                )

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        temp_xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("xml_file_name"),
        )
        self.assertTrue(temp_xml_file_path in temp_dir_files)

        # assert statuses
        status_assertion_map = {
            "sub_article": "expected_sub_article_status",
            "modify_xml": "expected_modify_xml_status",
            "modify_manifest_xml": "expected_modify_manifest_xml_status",
            "modify_files": "expected_modify_files_status",
            "upload_xml": "expected_upload_xml_status",
        }
        for status_value, assert_value in status_assertion_map.items():
            self.assertEqual(
                self.activity.statuses.get(status_value),
                test_data.get(assert_value),
                "failed comparing status {status_value} in {comment}".format(
                    status_value=status_value, comment=test_data.get("comment")
                ),
            )

        # assertion on XML contents
        if test_data.get("expected_xml_contains") or test_data.get(
            "expected_xml_not_contains"
        ):
            with open(temp_xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains", []):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )
            for fragment in test_data.get("expected_xml_not_contains", []):
                self.assertTrue(
                    fragment not in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        manifest_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        if test_data.get("expected_manifest_xml_contains") or test_data.get(
            "expected_manifest_xml_not_contains"
        ):
            with open(manifest_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_manifest_xml_contains", []):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )
            for fragment in test_data.get("expected_manifest_xml_not_contains", []):
                self.assertTrue(
                    fragment not in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
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


class TestFindGraphicTags(unittest.TestCase):
    "tests for find_graphic_tags()"

    def test_find_graphic_tags(self):
        "test finding graphic XML tags"
        root = ElementTree.fromstring(
            '<root xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<graphic mime-subtype="jpg"'
            ' xlink:href="elife-99548-sa1-fig1.jpg" mimetype="image"/>'
            "</root>"
        )
        result = activity_module.find_graphic_tags(root)
        self.assertEqual(len(result), 1)

    def test_none(self):
        "test if root is None"
        result = activity_module.find_graphic_tags(None)
        self.assertEqual(result, [])


class TestFindInlineGraphicTags(unittest.TestCase):
    "tests for find_inline_graphic_tags()"

    def test_find_inline_graphic_tags(self):
        "test finding inline-graphic XML tags"
        root = ElementTree.fromstring(
            '<root xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<inline-graphic xlink:href="elife-99548-sa1-fig1.jpg"/>'
            "</root>"
        )
        result = activity_module.find_inline_graphic_tags(root)
        self.assertEqual(len(result), 1)

    def test_none(self):
        "test if root is None"
        result = activity_module.find_inline_graphic_tags(None)
        self.assertEqual(result, [])
