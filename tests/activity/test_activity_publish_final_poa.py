import unittest
import glob
import os
import time
import zipfile
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data, unpack
import activity.activity_PublishFinalPOA as activity_module
from activity.activity_PublishFinalPOA import activity_PublishFinalPOA
from tests.classes_mock import FakeSMTPServer
from tests.activity import helpers, settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


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
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

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
    @patch("provider.lax_provider.article_publication_date")
    @patch.object(activity_PublishFinalPOA, "next_revision_number")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_PublishFinalPOA, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_provider_storage_context,
        fake_outbox_key_names,
        fake_next_revision_number,
        fake_get_pub_date_str_from_lax,
        fake_email_smtp_connect,
    ):

        fake_email_smtp_connect.return_value = FakeSMTPServer(self.poa.get_tmp_dir())
        fake_clean_tmp_dir.return_value = None
        fake_provider_storage_context.return_value = FakeStorageContext(
            "tests/test_data/poa/outbox"
        )
        fake_storage_context.return_value = FakeStorageContext()
        fake_next_revision_number.return_value = 1
        # fake_upload_files_to_s3.return_value = True
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
            self.poa.clean_from_outbox_files = []
            self.poa.done_xml_files = []
            self.poa.malformed_ds_file_names = []
            self.poa.empty_ds_file_names = []
            self.poa.unmatched_ds_file_names = []

    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_module, "storage_context")
    def test_next_revision_number_default(
        self, fake_storage_context, fake_list_resources
    ):
        doi_id = "7"
        key_names = []
        expected = 1
        fake_storage_context.return_value = FakeStorageContext()
        fake_list_resources.return_value = key_names
        self.assertEqual(self.poa.next_revision_number(doi_id), expected)

    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(activity_module, "storage_context")
    def test_next_revision_number_next(self, fake_storage_context, fake_list_resources):
        doi_id = "7"
        key_names = ["elife-00007-poa-r1.zip", "elife-00007-poa-r_bad_number.zip"]
        expected = 2
        fake_storage_context.return_value = FakeStorageContext()
        fake_list_resources.return_value = key_names
        self.assertEqual(self.poa.next_revision_number(doi_id), expected)


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


@ddt
class TestDoiIdFromFilename(unittest.TestCase):
    @data(
        (None, None),
        ("", None),
        ("decap_elife_poa_e10727.pdf", 10727),
        ("decap_elife_poa_e12029v2.pdf", 12029),
        ("elife_poa_e10727.xml", 10727),
        ("elife_poa_e10727_ds.zip", 10727),
        ("elife_poa_e12029v2.xml", 12029),
        ("bad_file_name.xml", None),
    )
    @unpack
    def test_doi_id_from_filename(self, filename, expected):
        doi_id = activity_module.doi_id_from_filename(filename)
        self.assertEqual(doi_id, expected)


class TestGetPubDateIfMissing(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    @patch.object(activity_module, "get_pub_date_str_from_lax")
    def test_get_pub_date_if_missing_lax(self, fake_get_pub_date):
        doi_id = 666
        fake_get_pub_date.return_value = "20160704000000"
        expected = time.strptime("2016-07-04T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        pub_date = activity_module.get_pub_date_if_missing(
            doi_id, settings_mock, self.logger
        )
        self.assertEqual(pub_date, expected)

    @patch("time.gmtime")
    @patch.object(activity_module, "get_pub_date_str_from_lax")
    def test_get_pub_date_if_missing_no_lax(self, fake_get_pub_date, fake_gmtime):
        fake_get_pub_date.return_value = None
        struct_time = time.strptime("2016-07-04T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        fake_gmtime.return_value = struct_time
        doi_id = 666
        expected = struct_time
        pub_date = activity_module.get_pub_date_if_missing(
            doi_id, settings_mock, self.logger
        )
        self.assertEqual(pub_date, expected)


class TestModifyXml(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    @patch.object(activity_module, "convert_xml")
    def test_modify_xml_exception(self, fake_convert_xml):
        fake_convert_xml.side_effect = Exception("An exception")
        doi_id = 666
        return_value = activity_module.modify_xml(
            None, doi_id, None, settings_mock, self.logger
        )
        self.assertEqual(return_value, False)
        self.assertEqual(
            self.logger.logexception,
            "Exception when converting XML for doi %s, An exception" % doi_id,
        )


class TestCheckMatchingXmlFile(unittest.TestCase):
    @patch("glob.glob")
    def test_check_matching_xml_file(self, fake_glob):
        zip_filename = "elife_poa_e14692_ds.zip"
        fake_glob.return_value = ["input_dir/elife_poa_e14692.xml"]
        self.assertTrue(
            activity_module.check_matching_xml_file(zip_filename, input_dir="")
        )

    @patch("glob.glob")
    def test_check_matching_xml_file_not_found(self, fake_glob):
        zip_filename = "elife_poa_e14692_ds.zip"
        fake_glob.return_value = ["input_dir/not_found.xml"]
        self.assertEqual(
            activity_module.check_matching_xml_file(zip_filename, input_dir=""), False
        )


class TestCheckMatchingPdfFile(unittest.TestCase):
    @patch("glob.glob")
    def test_check_matching_pdf_file(self, fake_glob):
        zip_filename = "elife_poa_e14692_ds.zip"
        fake_glob.return_value = ["input_dir/decap_elife_poa_e14692.pdf"]
        self.assertTrue(
            activity_module.check_matching_pdf_file(zip_filename, input_dir="")
        )

    @patch("glob.glob")
    def test_check_matching_pdf_file_not_found(self, fake_glob):
        zip_filename = "elife_poa_e14692_ds.zip"
        fake_glob.return_value = ["input_dir/not_found.pdf"]
        self.assertEqual(
            activity_module.check_matching_pdf_file(zip_filename, input_dir=""), False
        )


class TestAddSelfUriToXml(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_add_self_uri_to_xml(self):
        file_name = "article.pdf"
        doi_id = 666
        xml_string = b"""<article>
    <front>
        <article-meta>
            <permissions />
        </article-meta>
    </front>
</article>"""
        root = ET.fromstring(xml_string)
        expected = b"""<article>
    <front>
        <article-meta>
            <permissions />
        <self-uri content-type="pdf" xlink:href="article.pdf" /></article-meta>
    </front>
</article>"""
        output = activity_module.add_self_uri_to_xml(
            doi_id, file_name, root, self.logger
        )
        self.assertEqual(ET.tostring(output), expected)

    def test_add_self_uri_to_xml_no_permissions_tag(self):
        file_name = "article.pdf"
        doi_id = 666
        xml_string = b"""<article>
    <front>
        <article-meta />
    </front>
</article>"""
        root = ET.fromstring(xml_string)
        expected = xml_string
        output = activity_module.add_self_uri_to_xml(
            doi_id, file_name, root, self.logger
        )
        self.assertEqual(ET.tostring(output), expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            "no permissions tag and no self-uri tag added: %s" % doi_id,
        )


class TestAddTagToXml(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_add_tag_to_xml(self):
        add_tag = Element("volume")
        add_tag.text = "1"
        doi_id = 666
        xml_string = b"""<article>
    <front>
        <article-meta>
            <elocation-id />
        </article-meta>
    </front>
</article>"""
        root = ET.fromstring(xml_string)
        expected = b"""<article>
    <front>
        <article-meta>
            <volume>1</volume><elocation-id />
        </article-meta>
    </front>
</article>"""
        output = activity_module.add_tag_to_xml_before_elocation_id(
            add_tag, root, doi_id, self.logger
        )
        self.assertEqual(ET.tostring(output), expected)

    def test_add_tag_to_xml_no_elocation_id_tag(self):
        add_tag = Element("foo")
        doi_id = 666
        xml_string = b"""<article>
    <front>
        <article-meta />
    </front>
</article>"""
        root = ET.fromstring(xml_string)
        expected = xml_string
        output = activity_module.add_tag_to_xml_before_elocation_id(
            add_tag, root, doi_id, self.logger
        )
        self.assertEqual(ET.tostring(output), expected)
        self.assertEqual(
            self.logger.loginfo[-1], "no elocation-id tag and no foo added: %s" % doi_id
        )


@ddt
class TestGetFilenameFromPath(unittest.TestCase):
    @data(
        ("elife_poa_e99999.xml", ".xml", "elife_poa_e99999"),
        (
            os.path.join("folder", "elife_poa_e99999_ds.zip"),
            "_ds.zip",
            "elife_poa_e99999",
        ),
    )
    @unpack
    def test_get_filename_from_path(self, file_path, extension, expected):
        self.assertEqual(
            activity_module.get_filename_from_path(file_path, extension), expected
        )


class TestCheckEmptySupplementalFiles(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_check_empty_supplemental_files(self):
        input_zipfile = "tests/test_data/poa/outbox/elife_poa_e13833_ds.zip"
        with zipfile.ZipFile(input_zipfile, "r") as current_zipfile:
            self.assertTrue(
                activity_module.check_empty_supplemental_files(current_zipfile)
            )

    def test_check_empty_supplemental_files_no_internal_zip(self):
        input_zipfile = "tests/test_data/poa/outbox/elife_poa_e99997_ds.zip"
        with zipfile.ZipFile(input_zipfile, "r") as current_zipfile:
            self.assertTrue(
                activity_module.check_empty_supplemental_files(current_zipfile)
            )

    def test_check_empty_supplemental_files_empty_internal_zip(self):
        directory = TempDirectory()
        internal_zip_path = os.path.join(directory.path, "internal.zip")
        with zipfile.ZipFile(internal_zip_path, "w") as input_zipfile:
            pass
        zip_file_path = os.path.join(directory.path, "empty.zip")
        with zipfile.ZipFile(zip_file_path, "w") as input_zipfile:
            input_zipfile.write(internal_zip_path, "elife13833_Supplemental_files.zip")
        with zipfile.ZipFile(zip_file_path, "r") as current_zipfile:
            self.assertEqual(
                activity_module.check_empty_supplemental_files(current_zipfile), False
            )


@ddt
class TestNewFilenameFromOld(unittest.TestCase):
    def setUp(self):
        self.new_filenames = [
            "elife-13833-supp.zip",
            "elife-13833.xml",
            "elife-13833.pdf",
            "fake_file",
        ]

    def test_new_filename_from_old(self):
        old_filename = "elife_poa_e13833_ds.zip"
        expected = "elife-13833-supp.zip"
        self.assertEqual(
            activity_module.new_filename_from_old(old_filename, self.new_filenames),
            expected,
        )

    @data(
        (None, None),
        ("", None),
        ("fake_file", "fake_file"),
        ("fake_file.", None),
        ("does_not_exist", None),
    )
    @unpack
    def test_new_filename_from_old_edge_cases(self, old_filename, expected):
        # edge cases for test coverage
        self.assertEqual(
            activity_module.new_filename_from_old(old_filename, self.new_filenames),
            expected,
        )


class TestNewZipFileName(unittest.TestCase):
    def test_new_zip_file_name(self):
        doi_id = "666"
        revision = "1"
        status = "poa"
        expected = "elife-00666-poa-r1.zip"
        self.assertEqual(
            activity_module.new_zip_file_name(doi_id, revision, status), expected
        )


class TestArticleXmlFromFilenameMap(unittest.TestCase):
    def test_article_xml_from_filename_map(self):
        filenames = ["elife_poa_e99999.xml"]
        expected = "elife_poa_e99999.xml"
        self.assertEqual(
            activity_module.article_xml_from_filename_map(filenames), expected
        )

    def test_article_xml_from_filename_map_not_found(self):
        filenames = ["elife_poa_e99999_ds.zip"]
        expected = None
        self.assertEqual(
            activity_module.article_xml_from_filename_map(filenames), expected
        )
