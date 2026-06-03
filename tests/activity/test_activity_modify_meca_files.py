# coding=utf-8

import copy
import importlib
import json
import os
import shutil
import unittest
import zipfile
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

# MECA zip fixture subfolder name values
FROM_ZIP_SUB_FOLDER = "content"
TO_ZIP_SUB_FOLDER = "foo"


def repackage_meca_file(meca_file_path, temp_dir):
    "rename files in MECA test fixture to use a subfolder other than content"
    # copy the MECA file to a temporary location
    meca_file_name = meca_file_path.rsplit(os.sep, 1)[-1]
    repackaged_meca_file_path = os.path.join(temp_dir, meca_file_name)
    shutil.copyfile(meca_file_path, repackaged_meca_file_path)

    # new zip subfolder name
    from_zip_sub_folder = FROM_ZIP_SUB_FOLDER.lstrip(os.sep)
    to_zip_sub_folder = TO_ZIP_SUB_FOLDER.lstrip(os.sep)

    # folder to store unzipped files
    zip_temp_dir = os.path.join(temp_dir, "zip_temp_dir")

    # expand the MECA file
    helpers.unzip_fixture(repackaged_meca_file_path, zip_temp_dir)

    # rename files in the zip file
    os.mkdir(os.path.join(zip_temp_dir, to_zip_sub_folder))
    for file_name in os.listdir(os.path.join(zip_temp_dir, from_zip_sub_folder)):
        shutil.move(
            os.path.join(zip_temp_dir, from_zip_sub_folder, file_name),
            os.path.join(zip_temp_dir, to_zip_sub_folder, file_name),
        )

    # also test a sub subfolder file
    sub_sub_folder = "subfolder"
    sub_sub_folder_path = os.path.join(to_zip_sub_folder, sub_sub_folder)
    os.makedirs(os.path.join(zip_temp_dir, sub_sub_folder_path), exist_ok=True)
    sub_sub_folder_file = "test.txt"
    with open(
        os.path.join(zip_temp_dir, sub_sub_folder_path, sub_sub_folder_file),
        "w",
        encoding="utf-8",
    ) as open_file:
        open_file.write("test")

    # change file paths in the manifest.xml file
    manifest_file_path = os.path.join(zip_temp_dir, "manifest.xml")
    with open(manifest_file_path, "r", encoding="utf-8") as open_file:
        manifest_content = open_file.read()
    manifest_content = manifest_content.replace(
        'href="%s/' % from_zip_sub_folder, 'href="%s/' % to_zip_sub_folder
    )
    # also add XML for the subfolder file
    manifest_content = manifest_content.replace(
        "</manifest>",
        '<item>\n<instance href="%s"/>\n</item>\n</manifest>'
        % os.path.join(sub_sub_folder_path, sub_sub_folder_file),
    )
    with open(manifest_file_path, "w", encoding="utf-8") as open_file:
        open_file.write(manifest_content)

    # rezip the MECA file
    with zipfile.ZipFile(repackaged_meca_file_path, "w") as open_zip:
        for file_name in os.listdir(zip_temp_dir):
            open_zip.write(os.path.join(zip_temp_dir, file_name), file_name)
        for file_name in os.listdir(os.path.join(zip_temp_dir, to_zip_sub_folder)):
            file_path = "%s/%s" % (to_zip_sub_folder, file_name)
            open_zip.write(os.path.join(zip_temp_dir, file_path), file_path)
        for file_name in os.listdir(os.path.join(zip_temp_dir, sub_sub_folder_path)):
            file_path = "%s/%s" % (sub_sub_folder_path, file_name)
            open_zip.write(os.path.join(zip_temp_dir, file_path), file_path)

    return repackaged_meca_file_path


def format_json_string(json_string):
    "from a log file entry, format the quotation marks to make it parsable as json"
    return (
        json_string.replace("{'", '{"')
        .replace("': '", '": "')
        .replace("': '", '": "')
        .replace("', '", '", "')
        .replace("'}", '"}')
    )


class TestModifyMecaFiles(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session_dict = copy.copy(SESSION_DICT)
        self.session_dict[
            "article_xml_path"
        ] = "%s/24301711.xml" % TO_ZIP_SUB_FOLDER.lstrip(os.sep)
        self.session = FakeSession(self.session_dict)
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
        "test a non- silent-correction workflow which change the content subfolder of the MECA"
        directory = TempDirectory()

        fake_session.return_value = self.session

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # repackage the meca file contents using a subfolder not named content
        repackage_temp_dir = os.path.join(directory.path, "repackage")
        os.mkdir(repackage_temp_dir)
        repackaged_meca_file_path = repackage_meca_file(
            meca_file_path, repackage_temp_dir
        )

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            repackaged_meca_file_path,
            self.session_dict,
            test_data={},
            temp_dir=directory.path,
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
            self.session_dict.get("expanded_folder"),
        )

        # manifest.xml
        manifest_file_path = os.path.join(
            expanded_folder_path,
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        expected_manifest_xml_contains = [
            '<item type="article" id="elife-95901-v1">',
            '<instance media-type="application/xml" href="%s/elife-preprint-95901-v1.xml"/>'
            % "content",
            '<instance media-type="image/tiff" href="content/24301711v1_fig1.tif"/>',
        ]
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

        # assertions on log contents
        self.assertTrue(
            (
                "ModifyMecaFiles, file_paths to move: "
                "['foo/24301711.pdf', 'foo/24301711.xml', 'foo/24301711v1_fig1.tif',"
                " 'foo/24301711v1_tbl1.tif', 'foo/24301711v1_tbl1a.tif',"
                " 'foo/24301711v1_tbl2.tif', 'foo/24301711v1_tbl3.tif',"
                " 'foo/24301711v1_tbl4.tif', 'foo/subfolder/test.txt']"
            )
            in self.activity.logger.loginfo
        )

        # assert the file_transfer_map dict in the log
        file_transfer_map_log_fragment = "ModifyMecaFiles, file_transfer_map:"
        file_transfer_map_string = None
        file_transfer_map_expected = {
            "foo/24301711.pdf": "content/24301711.pdf",
            "foo/24301711.xml": "content/elife-preprint-95901-v1.xml",
            "foo/24301711v1_fig1.tif": "content/24301711v1_fig1.tif",
            "foo/24301711v1_tbl1.tif": "content/24301711v1_tbl1.tif",
            "foo/24301711v1_tbl1a.tif": "content/24301711v1_tbl1a.tif",
            "foo/24301711v1_tbl2.tif": "content/24301711v1_tbl2.tif",
            "foo/24301711v1_tbl3.tif": "content/24301711v1_tbl3.tif",
            "foo/24301711v1_tbl4.tif": "content/24301711v1_tbl4.tif",
            "foo/subfolder/test.txt": "content/subfolder/test.txt",
        }
        for line in self.activity.logger.loginfo:
            if line.startswith("%s {" % file_transfer_map_log_fragment):
                file_transfer_map_string = format_json_string(
                    line.rsplit(file_transfer_map_log_fragment, 1)[-1]
                )
        self.assertDictEqual(
            json.loads(file_transfer_map_string), file_transfer_map_expected
        )

        # assert S3 bucket expanded folder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(
                        directory.path, self.session.get_value("expanded_folder")
                    )
                )
            ),
            [FROM_ZIP_SUB_FOLDER, "manifest.xml", "mimetype", "transfer.xml"],
        )
        # assert S3 bucket content subfolder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(
                        directory.path,
                        self.session.get_value("expanded_folder"),
                        FROM_ZIP_SUB_FOLDER,
                    )
                )
            ),
            [
                "24301711.pdf",
                "24301711v1_fig1.tif",
                "24301711v1_tbl1.tif",
                "24301711v1_tbl1a.tif",
                "24301711v1_tbl2.tif",
                "24301711v1_tbl3.tif",
                "24301711v1_tbl4.tif",
                "elife-preprint-95901-v1.xml",
                "subfolder",
            ],
        )

        # assert article XML path in the session is changed
        self.assertEqual(
            self.session.get_value("article_xml_path"),
            "%s/elife-preprint-95901-v1.xml" % FROM_ZIP_SUB_FOLDER,
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_not_change_subfolder_name(
        self,
        fake_session,
        fake_storage_context,
    ):
        "test when the subfolder name is not changed but the article XML file name is changed"
        directory = TempDirectory()

        # switch back to using article XML in the default content folder
        session_dict = copy.copy(self.session_dict)
        session = copy.copy(self.session)
        self.session_dict[
            "article_xml_path"
        ] = "%s/24301711.xml" % FROM_ZIP_SUB_FOLDER.lstrip(os.sep)
        session.store_value(
            "article_xml_path", "%s/24301711.xml" % FROM_ZIP_SUB_FOLDER.lstrip(os.sep)
        )

        fake_session.return_value = session

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path,
            session_dict,
            test_data={},
            temp_dir=directory.path,
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
            session_dict.get("expanded_folder"),
        )

        # manifest.xml
        manifest_file_path = os.path.join(
            expanded_folder_path,
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        expected_manifest_xml_contains = [
            '<item type="article" id="elife-95901-v1">',
            '<instance media-type="application/xml" href="%s/elife-preprint-95901-v1.xml"/>'
            % FROM_ZIP_SUB_FOLDER,
        ]
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

        # assert S3 bucket expanded folder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(directory.path, session.get_value("expanded_folder"))
                )
            ),
            [FROM_ZIP_SUB_FOLDER, "manifest.xml", "mimetype", "transfer.xml"],
        )
        # assert S3 bucket content subfolder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(
                        directory.path,
                        session.get_value("expanded_folder"),
                        FROM_ZIP_SUB_FOLDER,
                    )
                )
            ),
            [
                "24301711.pdf",
                "24301711v1_fig1.tif",
                "24301711v1_tbl1.tif",
                "24301711v1_tbl1a.tif",
                "24301711v1_tbl2.tif",
                "24301711v1_tbl3.tif",
                "24301711v1_tbl4.tif",
                "elife-preprint-95901-v1.xml",
            ],
        )

        # assert article XML path in the session is changed
        self.assertEqual(
            session.get_value("article_xml_path"),
            "%s/elife-preprint-95901-v1.xml" % FROM_ZIP_SUB_FOLDER,
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity_silent_correction(
        self,
        fake_session,
        fake_storage_context,
    ):
        "test silent-correction run_type to rename meca files"
        directory = TempDirectory()

        # add run_type to test data
        session_dict = copy.copy(self.session_dict)
        session = copy.copy(self.session)
        session_dict["run_type"] = "silent-correction"
        session.store_value("run_type", "silent-correction")

        fake_session.return_value = session

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # repackage the meca file contents using a subfolder not named content
        repackage_temp_dir = os.path.join(directory.path, "repackage")
        os.mkdir(repackage_temp_dir)
        repackaged_meca_file_path = repackage_meca_file(
            meca_file_path, repackage_temp_dir
        )

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            repackaged_meca_file_path,
            session_dict,
            test_data={},
            temp_dir=directory.path,
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
            session_dict.get("expanded_folder"),
        )

        # manifest.xml
        manifest_file_path = os.path.join(
            expanded_folder_path,
            populated_data.get("manifest_file_name"),
        )

        # assertion on manifest XML contents
        expected_manifest_xml_contains = [
            '<item type="article" id="elife-95901-v1">',
            '<instance media-type="application/xml" href="%s/24301711.xml"/>'
            % TO_ZIP_SUB_FOLDER,
        ]
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

        # assert S3 bucket expanded folder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(directory.path, session.get_value("expanded_folder"))
                )
            ),
            [TO_ZIP_SUB_FOLDER, "manifest.xml", "mimetype", "transfer.xml"],
        )
        # assert S3 bucket content subfolder files
        self.assertEqual(
            sorted(
                os.listdir(
                    os.path.join(
                        directory.path,
                        session.get_value("expanded_folder"),
                        TO_ZIP_SUB_FOLDER,
                    )
                )
            ),
            [
                "24301711.pdf",
                "24301711.xml",
                "24301711v1_fig1.tif",
                "24301711v1_tbl1.tif",
                "24301711v1_tbl1a.tif",
                "24301711v1_tbl2.tif",
                "24301711v1_tbl3.tif",
                "24301711v1_tbl4.tif",
                "subfolder",
            ],
        )

        # assert article XML path in the session is changed
        self.assertEqual(
            self.session.get_value("article_xml_path"),
            "%s/24301711.xml" % TO_ZIP_SUB_FOLDER,
        )


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
