import unittest
import shutil
import glob
import os
import xml.etree.ElementTree as ET
from mock import patch
import activity.activity_PublishFinalPOA as activity_module
from activity.activity_PublishFinalPOA import activity_PublishFinalPOA
from tests.classes_mock import FakeSMTPServer
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


class TestPublishFinalPOA(unittest.TestCase):
    def setUp(self):
        self.poa = activity_PublishFinalPOA(
            settings_mock, FakeLogger(), None, None, None
        )

        self.do_activity_passes = []

        self.do_activity_passes.append(
            {
                "outbox_file_list": [],
                "done_dir_file_count": 0,
                "approve_status": False,
                "publish_status": None,
                "activity_status": True,
                "output_dir_files": [],
                "done_xml_files": [],
                "clean_from_outbox_files": [],
                "malformed_ds_file_names": [],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": [],
            }
        )

        # Missing a PDF
        self.do_activity_passes.append(
            {
                "outbox_file_list": ["elife_poa_e13833.xml", "elife_poa_e13833_ds.zip"],
                "done_dir_file_count": 0,
                "approve_status": True,
                "publish_status": True,
                "activity_status": True,
                "output_dir_files": [],
                "done_xml_files": [],
                "clean_from_outbox_files": [],
                "malformed_ds_file_names": [],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": ["elife_poa_e13833_ds.zip"],
            }
        )

        # Full set of files for one article
        self.do_activity_passes.append(
            {
                "outbox_file_list": [
                    "decap_elife_poa_e13833.pdf",
                    "elife_poa_e13833.xml",
                    "elife_poa_e13833_ds.zip",
                ],
                "done_dir_file_count": 3,
                "approve_status": True,
                "publish_status": True,
                "activity_status": True,
                "output_dir_files": ["elife-13833-poa-r1.zip"],
                "done_xml_files": ["elife-13833.xml"],
                "clean_from_outbox_files": [
                    "decap_elife_poa_e13833.pdf",
                    "elife_poa_e13833.xml",
                    "elife_poa_e13833_ds.zip",
                ],
                "malformed_ds_file_names": [],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": [],
            }
        )

        # One article with no ds.zip file
        self.do_activity_passes.append(
            {
                "outbox_file_list": [
                    "decap_elife_poa_e14692.pdf",
                    "elife_poa_e14692.xml",
                ],
                "done_dir_file_count": 2,
                "approve_status": True,
                "publish_status": True,
                "activity_status": True,
                "output_dir_files": ["elife-14692-poa-r1.zip"],
                "done_xml_files": ["elife-14692.xml"],
                "clean_from_outbox_files": [
                    "decap_elife_poa_e14692.pdf",
                    "elife_poa_e14692.xml",
                ],
                "malformed_ds_file_names": [],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": [],
            }
        )

        # Full set of files for two articles
        self.do_activity_passes.append(
            {
                "outbox_file_list": [
                    "decap_elife_poa_e13833.pdf",
                    "elife_poa_e13833.xml",
                    "elife_poa_e13833_ds.zip",
                    "decap_elife_poa_e14692.pdf",
                    "elife_poa_e14692.xml",
                    "elife_poa_e14692_ds.zip",
                    "elife_poa_e99999_ds.zip",
                    "elife_poa_e99997_ds.zip",
                ],
                "done_dir_file_count": 6,
                "approve_status": True,
                "publish_status": True,
                "activity_status": True,
                "output_dir_files": [
                    "elife-13833-poa-r1.zip",
                    "elife-14692-poa-r1.zip",
                ],
                "done_xml_files": ["elife-13833.xml", "elife-14692.xml"],
                "clean_from_outbox_files": [
                    "decap_elife_poa_e13833.pdf",
                    "elife_poa_e13833.xml",
                    "elife_poa_e13833_ds.zip",
                    "decap_elife_poa_e14692.pdf",
                    "elife_poa_e14692.xml",
                    "elife_poa_e14692_ds.zip",
                ],
                "malformed_ds_file_names": ["elife_poa_e99999_ds.zip"],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": ["elife_poa_e99997_ds.zip"],
            }
        )

        # Full set of files for one article
        self.do_activity_passes.append(
            {
                "outbox_file_list": [
                    "decap_elife_poa_e15082.pdf",
                    "elife_poa_e15082.xml",
                    "elife_poa_e15082_ds.zip",
                ],
                "done_dir_file_count": 3,
                "approve_status": True,
                "publish_status": True,
                "activity_status": True,
                "output_dir_files": ["elife-15082-poa-r1.zip"],
                "done_xml_files": ["elife-15082.xml"],
                "clean_from_outbox_files": [
                    "decap_elife_poa_e15082.pdf",
                    "elife_poa_e15082.xml",
                    "elife_poa_e15082_ds.zip",
                ],
                "malformed_ds_file_names": [],
                "empty_ds_file_names": [],
                "unmatched_ds_file_names": [],
            }
        )

        # Tests for values in the XML files after rewriting
        self.xml_file_values = {}
        self.xml_file_values["elife-13833.xml"] = {
            "./front/article-meta/volume": (None, "5"),
            "./front/article-meta/article-id[@pub-id-type='publisher-id']": (
                None,
                "13833",
            ),
            "./front/article-meta/pub-date[@date-type='pub']/day": (None, "05"),
            "./front/article-meta/pub-date[@date-type='pub']/month": (None, "07"),
            "./front/article-meta/pub-date[@date-type='pub']/year": (None, "2016"),
            "./front/article-meta/self-uri": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-13833.pdf",
            ),
        }
        self.xml_file_values["elife-14692.xml"] = {
            "./front/article-meta/volume": (None, "5"),
            "./front/article-meta/article-id[@pub-id-type='publisher-id']": (
                None,
                "14692",
            ),
            "./front/article-meta/pub-date[@date-type='pub']/day": (None, "04"),
            "./front/article-meta/pub-date[@date-type='pub']/month": (None, "07"),
            "./front/article-meta/pub-date[@date-type='pub']/year": (None, "2016"),
            "./front/article-meta/self-uri": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-14692.pdf",
            ),
        }
        self.xml_file_values["elife-15082.xml"] = {
            "./front/article-meta/volume": (None, "5"),
            "./front/article-meta/article-id[@pub-id-type='publisher-id']": (
                None,
                "15082",
            ),
            "./front/article-meta/pub-date[@date-type='pub']/day": (None, "13"),
            "./front/article-meta/pub-date[@date-type='pub']/month": (None, "07"),
            "./front/article-meta/pub-date[@date-type='pub']/year": (None, "2016"),
            "./front/article-meta/self-uri": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-15082.pdf",
            ),
        }

        # Tests for XML values only for when a ds zip file was packaged as part of the test
        self.xml_file_values_when_ds_zip = {}
        self.xml_file_values_when_ds_zip["elife-13833.xml"] = {
            "./back/sec/supplementary-material/ext-link": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-13833-supp.zip",
            ),
        }
        self.xml_file_values_when_ds_zip["elife-14692.xml"] = {
            "./back/sec/supplementary-material/ext-link": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-14692-supp.zip",
            ),
        }
        self.xml_file_values_when_ds_zip["elife-15082.xml"] = {
            "./back/sec/supplementary-material/ext-link": (
                "{http://www.w3.org/1999/xlink}href",
                "elife-15082-supp.zip",
            ),
        }

    def tearDown(self):
        self.poa.clean_tmp_dir()

    def remove_files_from_tmp_dir_subfolders(self):
        """
        Run between each test pass, delete the subfolders in tmp_dir
        """
        for directory in os.listdir(self.poa.get_tmp_dir()):
            directory_full_path = self.poa.get_tmp_dir() + os.sep + directory
            if os.path.isdir(directory_full_path):
                for file in glob.glob(directory_full_path + "/*"):
                    os.remove(file)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_PublishFinalPOA, "get_pub_date_str_from_lax")
    @patch.object(activity_PublishFinalPOA, "upload_files_to_s3")
    @patch.object(activity_PublishFinalPOA, "next_revision_number")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_PublishFinalPOA, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_outbox_key_names,
        fake_next_revision_number,
        fake_upload_files_to_s3,
        fake_get_pub_date_str_from_lax,
        fake_email_smtp_connect,
    ):

        fake_email_smtp_connect.return_value = FakeSMTPServer(self.poa.get_tmp_dir())
        fake_clean_tmp_dir.return_value = None
        fake_storage_context.return_value = FakeStorageContext(
            "tests/test_data/poa/outbox"
        )
        fake_next_revision_number.return_value = 1
        fake_upload_files_to_s3.return_value = True
        fake_get_pub_date_str_from_lax.return_value = "20160704000000"

        for test_data in self.do_activity_passes:

            fake_outbox_key_names.return_value = test_data["outbox_file_list"]

            param_data = None
            success = self.poa.do_activity(param_data)

            self.assertEqual(self.poa.approve_status, test_data["approve_status"])
            self.assertEqual(self.poa.publish_status, test_data["publish_status"])
            self.assertEqual(
                count_files_in_dir(self.poa.directories.get("DONE_DIR")),
                test_data["done_dir_file_count"],
            )
            self.assertEqual(self.poa.activity_status, test_data["activity_status"])
            self.assertTrue(
                compare_files_in_dir(
                    self.poa.directories.get("OUTPUT_DIR"),
                    test_data["output_dir_files"],
                )
            )
            self.assertEqual(
                sorted(self.poa.done_xml_files), sorted(test_data["done_xml_files"])
            )
            self.assertEqual(
                sorted(self.poa.clean_from_outbox_files),
                sorted(test_data["clean_from_outbox_files"]),
            )
            self.assertEqual(
                sorted(self.poa.malformed_ds_file_names),
                sorted(test_data["malformed_ds_file_names"]),
            )
            self.assertEqual(
                sorted(self.poa.empty_ds_file_names),
                sorted(test_data["empty_ds_file_names"]),
            )
            self.assertEqual(
                sorted(self.poa.unmatched_ds_file_names),
                sorted(test_data["unmatched_ds_file_names"]),
            )

            # Check XML values if XML was approved
            if test_data["done_dir_file_count"] > 0:
                xml_files = glob.glob(self.poa.directories.get("DONE_DIR") + "/*.xml")
                for xml_file in xml_files:
                    self.assertTrue(check_xml_contents(xml_file, self.xml_file_values))

                    # If a ds zip file for the article, check more XML elements
                    if ds_zip_in_list_of_files(
                        xml_file, self.poa.clean_from_outbox_files
                    ):
                        self.assertTrue(
                            check_xml_contents(
                                xml_file, self.xml_file_values_when_ds_zip
                            )
                        )

            self.assertEqual(True, success)

            # Clean the tmp_dir subfolders between tests
            self.remove_files_from_tmp_dir_subfolders()

            # Reset variables
            self.poa.activity_status = None
            self.poa.approve_status = None
            self.poa.publish_status = None
            self.poa.malformed_ds_file_names = []
            self.poa.empty_ds_file_names = []
            self.poa.unmatched_ds_file_names = []


def count_files_in_dir(dir_name):
    """
    After do_activity, check the directory contains a zip with ds_zip file name
    """
    file_names = glob.glob(dir_name + os.sep + "*")
    return len(file_names)


def compare_files_in_dir(dir_name, file_list):
    """
    Compare the file names in the directroy to the file_list provided
    """
    file_names = glob.glob(dir_name + os.sep + "*")
    # First check the count is the same
    if len(file_list) != len(file_names):
        return False
    # Then can compare file name by file name
    for file in file_names:
        file_name = file.split(os.sep)[-1]
        if file_name not in file_list:
            return False
    return True


def check_xml_contents(xml_file, xml_file_values):
    """
    Function to compare XML tag value as located by an xpath
    Can compare one tag only at a time
    """
    root = None
    xml_file_name = xml_file.split(os.sep)[-1]
    if xml_file_name in xml_file_values:
        ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
        root = ET.parse(xml_file)
    if root:
        for (xpath, (attribute, value)) in xml_file_values[xml_file_name].items():
            matched_tags = root.findall(xpath)
            if len(matched_tags) != 1:
                return False
            for matched_tag in matched_tags:
                if attribute:
                    if matched_tag.get(attribute) != value:
                        return False
                else:
                    if matched_tag.text != value:
                        return False

    return True


def ds_zip_in_list_of_files(xml_file, file_list):
    """
    Given an XML file and a list of files
    check the list of files contains a ds zip file that matches the xml file
    """
    doi_id = xml_file.split("-")[-1].split(".")[0]
    for file in file_list:
        if str(doi_id) in file and file.endswith("ds.zip"):
            return True
    return False


if __name__ == "__main__":
    unittest.main()
