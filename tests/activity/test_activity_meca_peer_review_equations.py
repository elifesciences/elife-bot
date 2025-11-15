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
from elifecleaner.transform import ArticleZipFile
from provider import cleaner, github_provider, peer_review
import activity.activity_MecaPeerReviewEquations as activity_module
from activity.activity_MecaPeerReviewEquations import (
    activity_MecaPeerReviewEquations as activity_object,
)
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


@ddt
class TestMecaPeerReviewEquations(unittest.TestCase):
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

    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no inline-graphic",
            "image_names": None,
            "expected_result": True,
            "expected_hrefs_status": None,
            "expected_modify_xml_status": None,
            "expected_modify_manifest_xml_status": None,
            "expected_rename_files_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "MecaPeerReviewEquations, no inline-graphic tags in "
                    "10.7554/eLife.95901.1"
                )
            ],
        },
        {
            "comment": "example with inline and block formulae",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph with an inline equation"
                ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
                "<p>Following is a display formula:</p>"
                '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": [
                "elife-inf1.jpg",
                "elife-inf2.jpg",
            ],
            "expected_result": True,
            "expected_hrefs_status": True,
            "expected_modify_xml_status": True,
            "expected_modify_manifest_xml_status": True,
            "expected_rename_files_status": True,
            "expected_upload_xml_status": True,
            "expected_xml_contains": [
                (
                    '<sub-article id="sa1">\n'
                    "<body>\n"
                    "<p>First paragraph with an inline equation"
                    ' <inline-formula id="sa1equ1">'
                    '<inline-graphic xlink:href="elife-sa1-equ1.jpg"/></inline-formula>.</p>\n'
                    "<p>Following is a display formula:</p>\n"
                    '<disp-formula id="sa1equ2">\n'
                    '<graphic mimetype="image" mime-subtype="jpg"'
                    ' xlink:href="elife-sa1-equ2.jpg"/>\n'
                    "</disp-formula>\n"
                    "</body>\n"
                    "</sub-article>\n"
                    "</article>"
                ),
            ],
            "expected_manifest_xml_contains": [
                (
                    '<item id="sa1equ1" type="equation">\n'
                    '<instance href="content/elife-sa1-equ1.jpg" media-type="image/jpeg"/>\n'
                    "</item>\n"
                    '<item id="sa1equ2" type="equation">\n'
                    '<instance href="content/elife-sa1-equ2.jpg" media-type="image/jpeg"/>\n'
                    "</item>\n"
                ),
            ],
            "expected_cleaner_log_contains": [
                "10.7554/eLife.95901.1 only inline-graphic tag found in p tag None of id None"
            ],
            "expected_bucket_upload_folder_contents": [
                "content/24301711.xml",
                "content/elife-sa1-equ2.jpg",
                "manifest.xml",
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
        fake_find_github_issues,
    ):
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
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

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        temp_xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("xml_file_name"),
        )
        self.assertTrue(temp_xml_file_path in temp_dir_files)

        # assert statuses
        status_assertion_map = {
            "hrefs": "expected_hrefs_status",
            "modify_xml": "expected_modify_xml_status",
            "modify_manifest_xml": "expected_modify_manifest_xml_status",
            "rename_files": "expected_rename_files_status",
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
        if test_data.get("expected_xml_contains"):
            with open(temp_xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains"):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

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

        # check output bucket folder contents
        if "expected_bucket_upload_folder_contents" in test_data:
            bucket_folder_path = os.path.join(
                dest_folder,
                SESSION_DICT.get("expanded_folder"),
            )
            output_bucket_list = helpers.list_files(bucket_folder_path)
            for bucket_file in test_data.get("expected_bucket_upload_folder_contents"):
                self.assertTrue(
                    bucket_file in output_bucket_list,
                    "%s not found in bucket upload folder" % bucket_file,
                )

    @patch.object(peer_review, "generate_inline_equation_file_transformations")
    @patch.object(peer_review, "generate_equation_file_transformations")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no equation file transformations",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph with an inline equation"
                ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": [
                "elife-inf1.jpg",
            ],
            "expected_result": True,
            "expected_hrefs_status": True,
            "expected_modify_xml_status": None,
            "expected_modify_manifest_xml_status": None,
            "expected_rename_files_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "MecaPeerReviewEquations, no file_transformations in "
                    "10.7554/eLife.95901.1"
                )
            ],
        },
    )
    def test_no_file_transformations(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_find_github_issues,
        fake_generate_equation,
        fake_generate_inline,
    ):
        "mock functions to test when there are no file transformations"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        fake_clean_tmp_dir.return_value = None
        fake_session.return_value = self.session

        fake_generate_equation.return_value = []
        fake_generate_inline.return_value = []

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

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        temp_xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("xml_file_name"),
        )
        self.assertTrue(temp_xml_file_path in temp_dir_files)

        # assert statuses
        status_assertion_map = {
            "hrefs": "expected_hrefs_status",
            "modify_xml": "expected_modify_xml_status",
            "modify_manifest_xml": "expected_modify_manifest_xml_status",
            "rename_files": "expected_rename_files_status",
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

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

    @patch.object(activity_object, "copy_expanded_folder_files")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @data(
        {
            "comment": "example with inline and block formulae",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph with an inline equation"
                ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
                "<p>Following is a display formula:</p>"
                '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": [
                "elife-inf1.jpg",
                "elife-inf2.jpg",
            ],
            "expected_result": True,
        },
    )
    def test_do_activity_copy_files_exception(
        self,
        test_data,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_find_github_issues,
        fake_copy_files,
    ):
        "test an exception raised when duplicating an image object in the bucket"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        fake_session.return_value = self.session

        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data, directory.path
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )
        fake_copy_files.side_effect = RuntimeError("An exception")

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, test_data.get("expected_result"))

    @patch.object(activity_object, "rename_expanded_folder_files")
    @patch.object(github_provider, "find_github_issues")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @data(
        {
            "comment": "example with inline and block formulae",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                "<p>First paragraph with an inline equation"
                ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
                "<p>Following is a display formula:</p>"
                '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": [
                "elife-inf1.jpg",
                "elife-inf2.jpg",
            ],
            "expected_result": True,
        },
    )
    def test_do_activity_rename_files_exception(
        self,
        test_data,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
        fake_find_github_issues,
        fake_rename_files,
    ):
        "test an exception raised when renaming an image object in the bucket"
        directory = TempDirectory()
        fake_find_github_issues.return_value = [FakeGithubIssue()]
        fake_session.return_value = self.session

        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data, directory.path
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )
        fake_rename_files.side_effect = RuntimeError("An exception")

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, test_data.get("expected_result"))


INLINE_FORMULA_XML = (
    "<p>First paragraph with an inline equation"
    ' <inline-formula id="sa1equ1">'
    '<inline-graphic xlink:href="elife-sa1-equ1.jpg"/></inline-formula>.</p>\n'
)

DISPLAY_FORMULA_XML = (
    "<p>Following is a display formula:</p>\n"
    '<disp-formula id="sa1equ2">\n'
    "<label>(1)</label>\n"
    '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ2.jpg"/>\n'
    "</disp-formula>\n"
)

INLINE_FILE_TRANSFORMATIONS = [
    (
        ArticleZipFile("sa1-fig1.jpg", "None", "None"),
        ArticleZipFile("elife-sa1-equ1.jpg", "None", "None"),
    )
]

DISPLAY_FILE_TRANSFORMATIONS = [
    (
        ArticleZipFile("sa1-fig2.jpg", "None", "None"),
        ArticleZipFile("elife-sa1-equ2.jpg", "None", "None"),
    )
]

INLINE_FILE_DETAILS = [
    {
        "file_type": "equation",
        "from_href": "sa1-fig1.jpg",
        "href": "elife-sa1-equ1.jpg",
        "id": "sa1equ1",
        "title": None,
    }
]

DISPLAY_FILE_DETAILS = [
    {
        "file_type": "equation",
        "from_href": "sa1-fig2.jpg",
        "href": "elife-sa1-equ2.jpg",
        "id": "sa1equ2",
        "title": "(1)",
    }
]


class TestCollectFormulaFileDetails(unittest.TestCase):
    "tests for collect_formula_file_details()"

    def test_collect_formula_file_details(self):
        "test collecting formula equation tag details"
        root = ElementTree.fromstring(
            (
                '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
                '<sub-article id="sa1">'
                "<body>"
                "%s"
                "%s"
                "</body>"
                "</sub-article>"
                "</article>"
            )
            % (INLINE_FORMULA_XML, DISPLAY_FORMULA_XML)
        )
        file_transformations = (
            INLINE_FILE_TRANSFORMATIONS + DISPLAY_FILE_TRANSFORMATIONS
        )
        content_subfolder = ""
        expected = DISPLAY_FILE_DETAILS + INLINE_FILE_DETAILS
        # invoke
        result = activity_module.collect_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)

    def test_no_formula_xml(self):
        "test if there are no disp-formula or inline-formula tags"
        root = ElementTree.fromstring("<article><sub-article /></article>")
        file_transformations = []
        content_subfolder = ""
        expected = []
        # invoke
        result = activity_module.collect_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)


class TestCollectDispFormulaFileDetails(unittest.TestCase):
    "tests for collect_disp_formula_file_details()"

    def test_collect_disp_formula_file_details(self):
        "test collecting disp-formula tag details"
        root = ElementTree.fromstring(
            (
                '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
                '<sub-article id="sa1">'
                "<body>"
                "%s"
                "</body>"
                "</sub-article>"
                "</article>"
            )
            % DISPLAY_FORMULA_XML
        )
        file_transformations = DISPLAY_FILE_TRANSFORMATIONS
        content_subfolder = ""
        expected = DISPLAY_FILE_DETAILS
        # invoke
        result = activity_module.collect_disp_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)

    def test_no_disp_formula(self):
        "test if there are no disp-formula tags"
        root = ElementTree.fromstring("<article><sub-article /></article>")
        file_transformations = []
        content_subfolder = ""
        expected = []
        # invoke
        result = activity_module.collect_disp_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)


class TestCollectInlineFormulaFileDetails(unittest.TestCase):
    "tests for collect_inline_formula_file_details()"

    def test_collect_inline_formula_file_details(self):
        "test collecting inline-formula tag details"
        root = ElementTree.fromstring(
            (
                '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
                '<sub-article id="sa1">'
                "<body>"
                "%s"
                "</body>"
                "</sub-article>"
                "</article>"
            )
            % INLINE_FORMULA_XML
        )
        file_transformations = INLINE_FILE_TRANSFORMATIONS
        content_subfolder = ""
        expected = INLINE_FILE_DETAILS
        # invoke
        result = activity_module.collect_inline_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)

    def test_no_inline_formula(self):
        "test if there are no inline-formula tags"
        root = ElementTree.fromstring("<article><sub-article /></article>")
        file_transformations = []
        content_subfolder = ""
        expected = []
        # invoke
        result = activity_module.collect_inline_formula_file_details(
            root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)
