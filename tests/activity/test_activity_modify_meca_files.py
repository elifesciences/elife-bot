# coding=utf-8

import copy
import importlib
import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
import docmaptools
import activity.activity_ModifyMecaFiles as activity_module
from activity.activity_ModifyMecaFiles import (
    activity_ModifyMecaFiles as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestModifyMecaFiles(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))
        self.session.store_value(
            "docmap_string", read_fixture("sample_docmap_for_95901.json")
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("docmap_string", None)
        # reload the module which had MagicMock applied to revert the mock
        importlib.reload(docmaptools)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()

        fake_session.return_value = self.session

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, test_data={}, temp_dir=directory.path
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=directory.path
        )

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)

        # assert statuses
        self.assertEqual(
            self.activity.statuses.get("modify_manifest_xml"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("modify_transfer_xml"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("upload"),
            True,
        )

        expanded_folder_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )

        # manifest.xml
        manifest_file_path = os.path.join(
            expanded_folder_path,
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        expected_manifest_xml_contains = ['<item type="article" id="elife-95901-v1">']
        expected_manifest_xml_does_not_contain = [
            '<item id="directives" type="x-hw-directives">'
        ]
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for fragment in expected_manifest_xml_contains:
            self.assertTrue(fragment in xml_content)
        for fragment in expected_manifest_xml_does_not_contain:
            self.assertTrue(fragment not in xml_content)

        # assert on bucket expanded folder contents
        expanded_folder_list = helpers.list_files(expanded_folder_path)
        self.assertTrue("directives.xml" not in expanded_folder_list)

        # transfer.xml
        transfer_file_path = os.path.join(
            expanded_folder_path,
            "transfer.xml",
        )
        # assertion on transfer XML contents
        expected_transfer_xml_contains = ["<acronym>eLife</acronym>"]
        expected_transfer_xml_does_not_contain = [
            'id="01c7bc4a-6e7f-1014-b5ad-cd90318f79f5"'
        ]
        with open(transfer_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        for fragment in expected_transfer_xml_contains:
            self.assertTrue(fragment in xml_content)
        for fragment in expected_transfer_xml_does_not_contain:
            self.assertTrue(fragment not in xml_content)


class TestClearManifestDirectivesItem(unittest.TestCase):
    "tests for clear_manifest_directives_item()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_clear_manifest_directives_item(self):
        "test removing item tag for directives.xml file in manifest.xml"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "10.7554/eLife.95901.1"
        xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item id="directives" type="x-hw-directives">'
            "<title>HWX Processing Directives</title>"
            '<instance media-type="application/vnd.hw-ingest-pi+xml" href="directives.xml"/>'
            "</item>"
            "</manifest>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        expected = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0"/>'
        )
        # invoke
        activity_module.clear_manifest_directives_item(xml_file_path, identifier)
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            result = open_file.read()
        self.assertEqual(result, expected)
