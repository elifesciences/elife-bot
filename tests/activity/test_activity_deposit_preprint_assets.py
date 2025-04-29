import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
import activity.activity_DepositPreprintAssets as activity_module
from activity.activity_DepositPreprintAssets import (
    activity_DepositPreprintAssets as activity_class,
)
from tests.activity import helpers, settings_mock
from tests.activity.classes_mock import FakeStorageContext, FakeSession, FakeLogger
from tests.activity import test_activity_data


SESSION_DICT = test_activity_data.post_preprint_publication_session_example()


class TestDepositPreprintAssets(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_activity_success(self, fake_storage_context, fake_session):
        directory = TempDirectory()

        expected_xml_file_name = "elife-preprint-95901-v2.xml"
        expected_pdf_file_name = "elife-preprint-95901-v2.pdf"

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )

        dest_folder = os.path.join(directory.path, "files_dest")
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )

        # rename the PDF file to reflect how it will look at this stage of the workflow
        expanded_folder_path = os.path.join(
            directory.path, SESSION_DICT.get("expanded_folder")
        )
        shutil.move(
            os.path.join(
                expanded_folder_path,
                "content",
                "24301711.pdf",
            ),
            os.path.join(
                expanded_folder_path,
                "content",
                expected_pdf_file_name,
            ),
        )
        manifest_xml_path = os.path.join(expanded_folder_path, "manifest.xml")
        with open(manifest_xml_path, "r", encoding="utf-8") as open_file:
            manifest_xml = open_file.read()
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(
                manifest_xml.replace(
                    'href="content/24301711.pdf"',
                    'href="content/%s"' % expected_pdf_file_name,
                )
            )

        fake_session.return_value = FakeSession(SESSION_DICT)

        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(self.activity.ACTIVITY_SUCCESS, result)
        # folder on disk to where bucket assets are copied
        cdn_folder = os.path.join(
            dest_folder, settings_mock.preprint_cdn_bucket.rsplit("/", 1)[-1], "95901"
        )
        # assert bucket folder contents
        self.assertEqual(
            sorted(os.listdir(cdn_folder)),
            sorted([expected_xml_file_name, expected_pdf_file_name]),
        )
        # assert log messages
        self.assertTrue(
            "DepositPreprintAssets, got article_pdf_path content/%s for 10.7554/eLife.95901.2"
            % expected_pdf_file_name
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "DepositPreprintAssets, assets to copy:"
                " {'content/%s': '%s', 'content/24301711.xml': '%s'}"
            )
            % (expected_pdf_file_name, expected_pdf_file_name, expected_xml_file_name)
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "DepositPreprintAssets, copying s3://bot_bucket/expanded_meca/95901-v2/"
                "1ee54f9a-cb28-4c8e-8232-4b317cf4beda/expanded_files/content/%s to"
                " s3://published/preprints/95901/%s"
            )
            % (expected_pdf_file_name, expected_pdf_file_name)
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "DepositPreprintAssets, copying s3://bot_bucket/expanded_meca/95901-v2/"
                "1ee54f9a-cb28-4c8e-8232-4b317cf4beda/expanded_files/content/24301711.xml to"
                " s3://published/preprints/95901/%s"
            )
            % (expected_xml_file_name)
            in self.activity.logger.loginfo
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_activity_permanent_failure(self, fake_storage_context, fake_session):
        "test exception raised copying assets"
        directory = TempDirectory()

        # populate the meca zip file and bucket folders for testing
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources")
        )

        fake_session.return_value = FakeSession(SESSION_DICT)

        # delete the XML file to cause a raised exception
        xml_file_path = os.path.join(
            directory.path, SESSION_DICT.get("expanded_folder"), "content/24301711.xml"
        )
        os.remove(xml_file_path)

        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, result)
