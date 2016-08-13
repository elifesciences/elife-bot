import unittest
from activity.activity_PMCDeposit import activity_PMCDeposit
import shutil
import zipfile
from mock import mock, patch
import settings_mock
from ddt import ddt, data, unpack
import time

import os
# Add parent directory for imports, so activity classes can use elife-poa-xml-generation
parentdir = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, parentdir)

@ddt
class TestPMCDeposit(unittest.TestCase):

    def setUp(self):
        self.activity = activity_PMCDeposit(settings_mock, None, None, None, None)

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
        dest_doc = self.activity.INPUT_DIR + os.sep + document
        #print dest_doc
        shutil.copy(source_doc, dest_doc)


    def zip_file_list(self, zip_file_name):
        file_list = None
        zip_file_path = self.activity.ZIP_DIR + os.sep + zip_file_name
        with zipfile.ZipFile(zip_file_path, 'r') as open_zip_file:
            file_list = open_zip_file.namelist()
        return file_list


    @patch('activity.activity_PMCDeposit.s3lib.get_s3_key_names_from_bucket')
    @patch('activity.activity_PMCDeposit.S3Connection')
    @patch.object(activity_PMCDeposit, 'upload_article_zip_to_s3')
    @patch.object(activity_PMCDeposit, 'ftp_to_endpoint')
    @patch.object(activity_PMCDeposit, 'download_files_from_s3')
    def test_do_activity(self, fake_download_files_from_s3, fake_ftp_to_endpoint,
                         fake_upload_article_zip_to_s3, fake_s3_mock, fake_s3_key_names):

        self.activity.create_activity_directories()

        for test_data in self.do_activity_passes:

            document = test_data["input_data"]["data"]["document"]

            fake_download_files_from_s3 = self.fake_download_files_from_s3(document)
            fake_s3_key_names.return_value = test_data["pmc_zip_key_names"]

            success = self.activity.do_activity(test_data["input_data"])

            self.assertEqual(True, success)
            self.assertEqual(self.activity.zip_file_name, test_data["expected_zip_filename"])
            self.assertEqual(self.zip_file_list(self.activity.zip_file_name),
                             test_data["zip_file_names"])


    @data(
        (None, [""]),
        (1, ["e@example.org", "life@example.org"])
    )
    @unpack
    def test_email_recipients(self, revision, expected_recipients):
        recipients = self.activity.email_recipients(revision)
        self.assertEqual(recipients, expected_recipients)


    @data(
        (None, None),
        (1, "Production please forward this to PMC with details of what changed")
    )
    @unpack
    def test_email_body_revision_header(self, revision, expected_header):
        header = self.activity.email_body_revision_header(revision)
        self.assertEqual(header, expected_header)


    @data(
        (1471046585, "elife", 5, "00013", None, 1, 2,
         "elife PMC deposit 2016-08-13 00:03, article 00013"),
        (1471046585, "elife", 5, "00013", 2, 1, 2,
         "elife PMC deposit 2016-08-13 00:03, article 00013, revision 2"),
    )
    @unpack
    def test_get_email_subject(self, timestamp, journal, volume, fid, revision,
                                         file_name, file_size, expected_subject):

        current_time = time.gmtime(timestamp)
        subject = self.activity.get_email_subject(current_time, journal, volume, fid, revision,
                                         file_name, file_size)
        self.assertEqual(subject, expected_subject)



if __name__ == '__main__':
    unittest.main()
