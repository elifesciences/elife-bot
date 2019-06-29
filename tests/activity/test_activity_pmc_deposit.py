import unittest
from activity.activity_PMCDeposit import activity_PMCDeposit
from collections import OrderedDict
import shutil
import zipfile
from mock import mock, patch
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from ddt import ddt, data, unpack
import time

import os


@ddt
class TestPMCDeposit(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PMCDeposit(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()

        self.do_activity_passes = []

        self.do_activity_passes.append({
            "input_data": {"data": {"document": "elife-19405-vor-v1-20160802113816.zip"}},
            "pmc_zip_key_names": [],
            "expected_zip_filename": "elife-05-19405.zip",
            "zip_file_names": ['elife-19405-fig1.tif', 'elife-19405-inf1.tif',
                               'elife-19405.pdf', 'elife-19405.xml']})

        self.do_activity_passes.append({
            "input_data": {"data": {"document": "elife-19405-vor-v1-20160802113816.zip"}},
            "pmc_zip_key_names": ["pmc/zip/elife-05-19405.zip"],
            "expected_zip_filename": "elife-05-19405.r1.zip",
            "zip_file_names": ['elife-19405-fig1.tif', 'elife-19405-inf1.tif',
                               'elife-19405.pdf', 'elife-19405.xml']})

        self.do_activity_passes.append({
            "input_data": {"data": {"document": "elife-19405-vor-v1-20160802113816.zip"}},
            "pmc_zip_key_names": ["pmc/zip/elife-05-19405.zip", "pmc/zip/elife-05-19405.r1.zip"],
            "expected_zip_filename": "elife-05-19405.r2.zip",
            "zip_file_names": ['elife-19405-fig1.tif', 'elife-19405-inf1.tif',
                               'elife-19405.pdf', 'elife-19405.xml']})

    def tearDown(self):
        self.activity.clean_tmp_dir()


    def fake_download_files_from_s3(self, document):
        source_doc = "tests/test_data/pmc/" + document
        #print source_doc
        dest_doc = self.activity.directories.get("INPUT_DIR") + os.sep + document
        #print dest_doc
        shutil.copy(source_doc, dest_doc)


    def zip_file_list(self, zip_file_name):
        file_list = None
        zip_file_path = self.activity.directories.get("ZIP_DIR") + os.sep + zip_file_name
        with zipfile.ZipFile(zip_file_path, 'r') as open_zip_file:
            file_list = open_zip_file.namelist()
        return file_list

    @patch.object(activity_PMCDeposit, 'clean_tmp_dir')
    @patch('activity.activity_PMCDeposit.s3lib.get_s3_key_names_from_bucket')
    @patch('activity.activity_PMCDeposit.S3Connection')
    @patch.object(activity_PMCDeposit, 'upload_article_zip_to_s3')
    @patch.object(activity_PMCDeposit, 'ftp_to_endpoint')
    @patch.object(activity_PMCDeposit, 'download_files_from_s3')
    def test_do_activity(self, fake_download_files_from_s3, fake_ftp_to_endpoint,
                         fake_upload_article_zip_to_s3, fake_s3_mock, fake_s3_key_names,
                         fake_clean_tmp_dir):

        for test_data in self.do_activity_passes:

            document = test_data["input_data"]["data"]["document"]

            fake_download_files_from_s3 = self.fake_download_files_from_s3(document)
            fake_s3_key_names.return_value = test_data["pmc_zip_key_names"]
            fake_ftp_to_endpoint.return_value = True

            success = self.activity.do_activity(test_data["input_data"])

            self.assertEqual(True, success)
            self.assertEqual(self.activity.zip_file_name, test_data["expected_zip_filename"])
            self.assertEqual(sorted(self.zip_file_list(self.activity.zip_file_name)),
                             sorted(test_data["zip_file_names"]))

    @patch('activity.activity_PMCDeposit.s3lib.get_s3_key_names_from_bucket')
    @patch('activity.activity_PMCDeposit.S3Connection')
    @patch.object(activity_PMCDeposit, 'upload_article_zip_to_s3')
    @patch.object(activity_PMCDeposit, 'ftp_to_endpoint')
    @patch.object(activity_PMCDeposit, 'download_files_from_s3')
    def test_do_activity_failed_ftp_to_endpoint(self, fake_download_files_from_s3, fake_ftp_to_endpoint,
                         fake_upload_article_zip_to_s3, fake_s3_mock, fake_s3_key_names):

        test_data = self.do_activity_passes[0]

        document = test_data["input_data"]["data"]["document"]

        fake_download_files_from_s3 = self.fake_download_files_from_s3(document)
        fake_s3_key_names.return_value = test_data["pmc_zip_key_names"]
        fake_ftp_to_endpoint.return_value = False

        success = self.activity.do_activity(test_data["input_data"])

        self.assertEqual(False, success)

    @patch('provider.article_processing.file_list')
    @data(
        (
            ['folder_name/elife-36842-v2.xml'],
             'folder_name/elife-36842-v2.xml'
        ),
        (
            ['folder_name/elife-36842-supp9-v2.xml', 'folder_name/elife-36842-v2.xml'],
             'folder_name/elife-36842-v2.xml'
        ),
    )
    @unpack
    def test_article_xml_file(self, list_of_files, expected, fake_file_list):
        fake_file_list.return_value = list_of_files
        self.assertEqual(self.activity.article_xml_file(), expected)


if __name__ == '__main__':
    unittest.main()
