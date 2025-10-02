# coding=utf-8

import unittest
import os
import shutil
import copy
from xml.etree import ElementTree
import zipfile
from mock import patch
from testfixtures import TempDirectory
import activity.activity_ReplacePreprintPDF as activity_module
from activity.activity_ReplacePreprintPDF import (
    activity_ReplacePreprintPDF as activity_class,
)
from tests import list_files
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)


SESSION_DICT = test_activity_data.ingest_meca_session_example()


def remove_pdf_from_manifest(manifest_file_path):
    "remove the PDF XML from manifest.xml for testing"
    with open(manifest_file_path, "r", encoding="utf-8") as open_file:
        manifest_xml_content = open_file.read()
    with open(manifest_file_path, "w", encoding="utf-8") as open_file:
        open_file.write(
            manifest_xml_content.replace(
                '<instance media-type="application/pdf" href="content/24301711.pdf"/>\n',
                "",
            )
        )


class TestReplacePreprintPdf(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_session,
        fake_storage_context,
        fake_get,
    ):
        "test if there is a pdf_url in the session"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        session_dict = copy.copy(SESSION_DICT)
        session_dict["pdf_url"] = pdf_url
        fake_session.return_value = FakeSession(session_dict)

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        fake_response = FakeResponse(200)
        # a PDF file to test with
        pdf_fixture = "tests/files_source/elife-00353-v1.pdf"
        with open(pdf_fixture, "rb") as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on statuses
        self.assertDictEqual(
            self.activity.statuses,
            {
                "pdf_url": True,
                "pdf_href": True,
                "download_pdf": True,
                "replace_pdf": True,
                "modify_manifest_xml": True,
                "upload_manifest_xml": True,
                "modify_article_xml": True,
                "upload_article_xml": True,
            },
        )

        # assertions on log
        self.assertTrue(
            (
                "ReplacePreprintPDF, got pdf_href content/24301711.pdf from"
                " manifest.xml for 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ReplacePreprintPDF, generated new PDF href value"
                " content/elife-preprint-95901-v1.pdf for 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ReplacePreprintPDF,"
                " downloading https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
                " to %s/content/elife-preprint-95901-v1.pdf for 10.7554/eLife.95901.1"
            )
            % self.activity.directories.get("INPUT_DIR")
            in self.activity.logger.loginfo,
        )

        self.assertTrue(
            (
                "ReplacePreprintPDF, copying new pdf content/elife-preprint-95901-v1.pdf"
                " to the bucket expanded folder"
            )
            in self.activity.logger.loginfo,
        )
        self.assertTrue(
            (
                "ReplacePreprintPDF, removing old pdf content/24301711.pdf"
                " from the bucket expanded folder"
            )
            in self.activity.logger.loginfo,
        )

        # assertions on files
        self.assertEqual(
            list_files(self.activity.directories.get("INPUT_DIR")),
            ["content/elife-preprint-95901-v1.pdf"],
        )

        # assertions on bucket contents
        bucket_expanded_folder_path = os.path.join(
            directory.path, session_dict.get("expanded_folder")
        )
        bucket_old_pdf_path = os.path.join(
            bucket_expanded_folder_path, "content/24301711.pdf"
        )
        self.assertFalse(
            os.path.exists(bucket_old_pdf_path),
            "Old PDF unexpectedly found in the bucket expanded folder",
        )
        bucket_new_pdf_path = os.path.join(
            bucket_expanded_folder_path, "content/elife-preprint-95901-v1.pdf"
        )
        self.assertTrue(
            os.path.exists(bucket_new_pdf_path),
            "New PDF missing from the bucket expanded folder",
        )
        self.assertEqual(
            os.stat(bucket_new_pdf_path).st_size,
            os.stat(pdf_fixture).st_size,
            "bucket PDF file size did not match the PDF fixture",
        )

        # assertion on XML contents
        temp_xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("xml_file_name"),
        )
        expected_xml_contains = [
            (
                "</permissions>\n"
                '<self-uri content-type="pdf" xlink:href="elife-preprint-95901-v1.pdf"/>'
            )
        ]
        expected_xml_not_contains = [
            '<self-uri xlink:href="24301711.pdf" content-type="pdf" xlink:role="full-text"/>'
        ]
        with open(temp_xml_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for fragment in expected_xml_contains:
            self.assertTrue(
                fragment in xml_content,
                "did not find %s in article XML" % fragment,
            )
        for fragment in expected_xml_not_contains:
            self.assertTrue(
                fragment not in xml_content,
                "unexpectedly found %s in article XML" % fragment,
            )

        # assertion on manifest XML contents
        manifest_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("manifest_file_name"),
        )
        expected_manifest_xml_contains = [
            (
                '<instance href="content/elife-preprint-95901-v1.pdf"'
                ' media-type="application/pdf"/>'
                "\n</item>"
            )
        ]
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for fragment in expected_manifest_xml_contains:
            self.assertTrue(
                fragment in xml_content, "did not find %s in manifest XML" % fragment
            )
        expected_manifest_xml_does_not_contain = [
            '<instance media-type="application/pdf" href="content/24301711.pdf"/>'
        ]
        for fragment in expected_manifest_xml_does_not_contain:
            self.assertTrue(
                fragment not in xml_content,
                "unexpectedly found %s in manifest XML" % fragment,
            )

    @patch("requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_same_pdf_file_name(
        self,
        fake_session,
        fake_storage_context,
        fake_get,
    ):
        "test if the new PDF file name is the same as the old PDF file name"
        directory = TempDirectory()

        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        session_dict = copy.copy(SESSION_DICT)
        session_dict["pdf_url"] = pdf_url
        fake_session.return_value = FakeSession(session_dict)

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )

        # rename the PDF file
        old_pdf_file_name = "24301711.pdf"
        new_pdf_file_name = "elife-preprint-95901-v1.pdf"
        content_subfolder = os.path.join(session_dict.get("expanded_folder"), "content")
        pdf_resource_path = os.path.join(content_subfolder, old_pdf_file_name)
        pdf_file_path = os.path.join(directory.path, pdf_resource_path)
        new_pdf_file_path = os.path.join(
            directory.path, content_subfolder, new_pdf_file_name
        )
        shutil.move(
            pdf_file_path,
            new_pdf_file_path,
        )
        populated_data["resources"] = [
            resource.replace(old_pdf_file_name, new_pdf_file_name)
            for resource in populated_data.get("resources")
        ]

        # rewrite the PDF tag from the manifest.xml
        manifest_file_path = os.path.join(
            directory.path, session_dict.get("expanded_folder"), "manifest.xml"
        )
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            manifest_content = open_file.read()
        with open(manifest_file_path, "w", encoding="utf-8") as open_file:
            manifest_content = open_file.write(
                manifest_content.replace(old_pdf_file_name, new_pdf_file_name)
            )

        # finish configuring the bucket storage fixtures
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        fake_response = FakeResponse(200)
        # a PDF file to test with
        pdf_fixture = "tests/files_source/elife-00353-v1.pdf"
        with open(pdf_fixture, "rb") as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on statuses
        self.assertDictEqual(
            self.activity.statuses,
            {
                "pdf_url": True,
                "pdf_href": True,
                "download_pdf": True,
                "replace_pdf": None,
                "modify_manifest_xml": True,
                "upload_manifest_xml": True,
                "modify_article_xml": True,
                "upload_article_xml": True,
            },
        )

        # assertions on bucket contents
        bucket_expanded_folder_path = os.path.join(
            directory.path, session_dict.get("expanded_folder")
        )
        bucket_new_pdf_path = os.path.join(
            bucket_expanded_folder_path, "content/elife-preprint-95901-v1.pdf"
        )
        self.assertTrue(
            os.path.exists(bucket_new_pdf_path),
            "New PDF missing from the bucket expanded folder",
        )
        self.assertEqual(
            os.stat(bucket_new_pdf_path).st_size,
            os.stat(pdf_fixture).st_size,
            "bucket PDF file size did not match the PDF fixture",
        )

        # assertions on log
        self.assertTrue(
            (
                "ReplacePreprintPDF, old pdf content/elife-preprint-95901-v1.pdf the same"
                " name as new pdf content/elife-preprint-95901-v1.pdf for 10.7554/eLife.95901.1"
            )
            in self.activity.logger.loginfo,
        )

    @patch("requests.get")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_class, "clean_tmp_dir")
    def test_no_meca_pdf_file(
        self,
        fake_clean_tmp_dir,
        fake_session,
        fake_storage_context,
        fake_get,
    ):
        "test if there is no PDF file in the MECA package"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        pdf_url = "https://example.org/raw/master/data/95901/v1/95901-v1.pdf"
        session_dict = copy.copy(SESSION_DICT)
        session_dict["pdf_url"] = pdf_url
        fake_session.return_value = FakeSession(session_dict)

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )
        # remove the PDF file
        pdf_resource_path = os.path.join(
            session_dict.get("expanded_folder"), "content", "24301711.pdf"
        )
        pdf_file_path = os.path.join(directory.path, pdf_resource_path)
        os.remove(pdf_file_path)
        populated_data["resources"] = [
            resource
            for resource in populated_data.get("resources")
            if resource != pdf_resource_path
        ]
        # remove the PDF tag from the manifest.xml
        manifest_file_path = os.path.join(
            directory.path, session_dict.get("expanded_folder"), "manifest.xml"
        )
        remove_pdf_from_manifest(manifest_file_path)

        # finish configuring the bucket storage fixtures
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        fake_response = FakeResponse(200)
        # a PDF file to test with
        pdf_fixture = "tests/files_source/elife-00353-v1.pdf"
        with open(pdf_fixture, "rb") as open_file:
            fake_response.content = open_file.read()
        fake_get.return_value = fake_response

        expected_result = activity_class.ACTIVITY_SUCCESS
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        # assertions on statuses
        self.assertDictEqual(
            self.activity.statuses,
            {
                "pdf_url": True,
                "pdf_href": True,
                "download_pdf": True,
                "replace_pdf": None,
                "modify_manifest_xml": True,
                "upload_manifest_xml": True,
                "modify_article_xml": True,
                "upload_article_xml": True,
            },
        )

        # assertions on bucket contents
        bucket_expanded_folder_path = os.path.join(
            directory.path, session_dict.get("expanded_folder")
        )
        bucket_new_pdf_path = os.path.join(
            bucket_expanded_folder_path, "content/elife-preprint-95901-v1.pdf"
        )
        self.assertTrue(
            os.path.exists(bucket_new_pdf_path),
            "New PDF missing from the bucket expanded folder",
        )
        self.assertEqual(
            os.stat(bucket_new_pdf_path).st_size,
            os.stat(pdf_fixture).st_size,
            "bucket PDF file size did not match the PDF fixture",
        )

        manifest_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        expected_manifest_xml_contains = [
            (
                '<instance href="content/elife-preprint-95901-v1.pdf"'
                ' media-type="application/pdf"/>'
                "\n</item>"
            )
        ]
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for fragment in expected_manifest_xml_contains:
            self.assertTrue(
                fragment in xml_content, "did not find %s in manifest XML" % fragment
            )
        expected_manifest_xml_does_not_contain = [
            '<instance media-type="application/pdf" href="content/24301711.pdf"/>'
        ]
        for fragment in expected_manifest_xml_does_not_contain:
            self.assertTrue(
                fragment not in xml_content,
                "unexpectedly found %s in manifest XML" % fragment,
            )

    @patch.object(activity_module, "get_session")
    def test_do_activity_no_pdf_url(
        self,
        fake_session,
    ):
        "test if no pdf_url is in the session"
        session_dict = copy.copy(SESSION_DICT)
        fake_session.return_value = FakeSession(session_dict)

        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)

        self.assertEqual(
            self.activity.logger.logerror,
            (
                "ReplacePreprintPDF, no pdf_url found in the session for"
                " 10.7554/eLife.95901.1, failing the workflow"
            ),
        )


class TestPdfHrefFromManifest(unittest.TestCase):
    "tests for pdf_href_from_manifest()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_pdf_href_from_manifest(self):
        "parse article PDF href from manifest.xml"
        directory = TempDirectory()
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        manifest_file_name = "manifest.xml"
        manifest_file_path = os.path.join(directory.path, manifest_file_name)
        with zipfile.ZipFile(meca_file_path) as open_zip:
            open_zip.extract("manifest.xml", directory.path)
        # invoke
        result = activity_module.pdf_href_from_manifest(manifest_file_path)
        # assert
        self.assertEqual(result, "content/24301711.pdf")

    def test_missing_instance_tag(self):
        "parse manifest.xml which is missing an article PDF href"
        directory = TempDirectory()
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        manifest_file_name = "manifest.xml"
        manifest_file_path = os.path.join(directory.path, manifest_file_name)
        with zipfile.ZipFile(meca_file_path) as open_zip:
            open_zip.extract("manifest.xml", directory.path)
        # remove the data
        remove_pdf_from_manifest(manifest_file_path)
        # invoke
        result = activity_module.pdf_href_from_manifest(manifest_file_path)
        # assert
        self.assertEqual(result, None)


class TestGenerateNewPdfHref(unittest.TestCase):
    "tests for generate_new_pdf_href()"

    def test_generate_new_pdf_href(self):
        "test generating a new PDF file XML href value"
        article_id = 95901
        version = 1
        content_subfolder = "content"
        expected = "content/elife-preprint-95901-v1.pdf"
        # invoke
        result = activity_module.generate_new_pdf_href(
            article_id, version, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)
