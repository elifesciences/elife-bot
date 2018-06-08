import unittest
from activity.activity_PackagePOA import activity_PackagePOA
import provider.lax_provider as lax_provider
from packagepoa import transform
import json
import shutil
from shutil import Error
import glob
from mock import mock, patch
import settings_mock
from tests.activity.classes_mock import FakeLogger

from types import MethodType

import os


class TestPackagePOA(unittest.TestCase):

    def setUp(self):
        self.poa = activity_PackagePOA(settings_mock, FakeLogger(), None, None, None)

        self.do_activity_passes = []
        self.do_activity_passes.append({
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            "doi": "10.7554/eLife.12717",
            "ds_zip": "elife_poa_e12717_ds.zip",
            "pub_date": "20160514000000"
        })
        self.do_activity_passes.append({
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            "doi": "10.7554/eLife.12717",
            "ds_zip": "elife_poa_e12717_ds.zip",
            "pub_date": None
        })

    def tearDown(self):
        self.poa.clean_tmp_dir()

    def fake_download_latest_csv(self):
        csv_files = glob.glob("tests/test_data/poa/*.csv")
        for file in csv_files:
            file_name = file.split(os.sep)[-1]
            shutil.copy(file, self.poa.CSV_DIR + os.sep + file_name)

    def fake_download_poa_zip(self, document):
        source_doc = "tests/test_data/poa/" + document
        dest_doc = self.poa.EJP_INPUT_DIR + os.sep + document
        shutil.copy(source_doc, dest_doc)
        self.poa.poa_zip_filename = dest_doc

    def fake_copy_pdf_to_hw_staging_dir(self, decap_pdf, junk_a, junk_b, junk_c, junk_d, junk_e):
        source_doc = "tests/test_data/poa/" + decap_pdf
        dest_doc = self.poa.DECAPITATE_PDF_DIR + os.sep + decap_pdf
        shutil.copy(source_doc, dest_doc)

    def fake_clean_tmp_dir(self):
        """
        Disable the default clean_tmp_dir() when do_activity runs
        so tests can introspect the files first
        Then can run clean_tmp_dir() in the tearDown later
        """
        pass

    def check_ds_zip_exists(self, ds_zip):
        """
        After do_activity, check the directory contains a zip with ds_zip file name
        """
        file_names = glob.glob(self.poa.OUTPUT_DIR + os.sep + "*")
        for file in file_names:
            if file.split(os.sep)[-1] == ds_zip:
                return True
        return False

    @patch.object(activity_PackagePOA, 'download_poa_zip')
    @patch.object(activity_PackagePOA, 'download_latest_csv')
    @patch.object(activity_PackagePOA, 'copy_files_to_s3_outbox')
    @patch.object(lax_provider, 'article_publication_date')
    @patch.object(activity_PackagePOA, 'clean_tmp_dir')
    def test_do_activity(self, fake_clean_tmp_dir, fake_article_publication_date,
                         fake_copy_files_to_s3_outbox,
                         fake_download_latest_csv, fake_download_poa_zip):

        for test_data in self.do_activity_passes:

            fake_download_latest_csv = self.fake_download_latest_csv()
            fake_download_poa_zip = self.fake_download_poa_zip(test_data["poa_input_zip"])
            if "pub_date" in test_data and test_data["pub_date"]:
                fake_article_publication_date.return_value = test_data["pub_date"]
            else:
                fake_article_publication_date.return_value = None
            fake_clean_tmp_dir = self.fake_clean_tmp_dir()

            # For now mock the PDF decapitator during tests
            transform.copy_pdf_to_output_dir = (
                MethodType(self.fake_copy_pdf_to_hw_staging_dir, test_data["poa_decap_pdf"]))

            param_data = json.loads('{"data": {"document": "' +
                                    test_data["poa_input_zip"] + '"}}')
            success = self.poa.do_activity(param_data)

            self.assertEqual(test_data["doi"], self.poa.doi)
            self.assertEqual(self.poa.generate_xml_status, True)
            self.assertEqual(self.poa.process_status, True)
            self.assertEqual(self.poa.approve_status, True)
            self.assertEqual(self.poa.pdf_decap_status, True)
            self.assertEqual(self.poa.activity_status, True)
            self.assertEqual(self.check_ds_zip_exists(test_data["ds_zip"]), True)
            self.assertEqual(True, success)


if __name__ == '__main__':
    unittest.main()
