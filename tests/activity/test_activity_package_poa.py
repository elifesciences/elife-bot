import unittest
from activity.activity_PackagePOA import activity_PackagePOA
import json
import shutil
import glob
from mock import mock, patch

import settings_mock

import os
# Add parent directory for imports, so activity classes can use elife-poa-xml-generation
parentdir = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, parentdir)

class TestPackagePOA(unittest.TestCase):
    def setUp(self):
        self.poa = activity_PackagePOA(settings_mock, None, None, None, None)

    def test_get_doi_id_from_doi(self):
        result = self.poa.get_doi_id_from_doi("10.7554/eLife.00003")
        self.assertEqual(result, 3)
        result = self.poa.get_doi_id_from_doi("not_a_doi")
        self.assertEqual(result, None)

    def copy_poa_csv(self):
        csv_files = glob.glob("tests/test_data/poa/*.csv")
        for file in csv_files:
            file_name = file.split(os.sep)[-1]
            shutil.copy(file, self.poa.elife_poa_lib.settings.XLS_PATH + file_name)

    @patch.object(activity_PackagePOA, 'download_poa_zip')
    @patch.object(activity_PackagePOA, 'download_latest_csv')
    @patch.object(activity_PackagePOA, 'copy_files_to_s3_outbox')
    def test_do_activity(self, fake_copy_files_to_s3_outbox, fake_download_latest_csv,
                         fake_download_poa_zip):

        self.poa.doi = "10.7554/eLife.00003"
        fake_download_latest_csv = self.copy_poa_csv()

        param_data = json.loads('{"data": {"document": "poa_test.zip"}}')
        success = self.poa.do_activity(param_data)

if __name__ == '__main__':
    unittest.main()
