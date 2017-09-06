import unittest
import shutil
import os
import zipfile
from activity.activity_FTPArticle import activity_FTPArticle
from mock import patch, MagicMock
import tests.activity.settings_mock as settings_mock
from ddt import ddt, data, unpack
from tests.activity.classes_mock import FakeLogger

@ddt
class TestFTPArticle(unittest.TestCase):

    def setUp(self):
        self.activity = activity_FTPArticle(settings_mock, FakeLogger(), None, None, None)

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch("provider.simpleDB")
    @patch.object(activity_FTPArticle, "ftp_to_endpoint")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', 'hefce_ftp.localhost', 'hefce_sftp.localhost', True),
        ('Cengage', 'cengage.localhost', None, True),
        ('GoOA', 'gooa.localhost', None, True),
        ('Scopus', 'scopus.localhost', None, True),
        ('WoS', 'wos.localhost', None, True),
        ('CNPIEC', 'cnpiec.localhost', None, True),
    )
    @unpack
    def test_do_activity(self, workflow, expected_ftp_uri, expected_sftp_uri, expected_result,
                         fake_sftp_to_endpoint, fake_ftp_to_endpoint, fake_simple_db,
                         fake_download_pmc_zip_from_s3):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp_to_endpoint = MagicMock()
        fake_simple_db = MagicMock()
        fake_download_pmc_zip_from_s3.return_value = True
        activity_data = {
            'data': {
                'elife_id': '19405',
                'workflow': workflow
            }
        }
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)
        self.assertEqual(self.activity.FTP_URI, expected_ftp_uri)
        self.assertEqual(self.activity.SFTP_URI, expected_sftp_uri)


    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch("provider.simpleDB")
    @patch.object(activity_FTPArticle, "ftp_to_endpoint")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', 'non_numeric_raises_exception', False),
    )
    @unpack
    def test_do_activity_failure(self, workflow, elife_id, expected_result,
                                 fake_sftp_to_endpoint, fake_ftp_to_endpoint, fake_simple_db,
                                 fake_download_pmc_zip_from_s3):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp_to_endpoint = MagicMock()
        fake_simple_db = MagicMock()
        fake_download_pmc_zip_from_s3 = MagicMock()
        # Cause an exception by setting elife_id as non numeric for now
        activity_data = {
            'data': {
                'elife_id': elife_id,
                'workflow': workflow
            }
        }
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)


    @data(
        ('tests/test_data/pmc/elife-05-19405.zip', 19405, 'Cengage', 'elife-19405-xml-pdf.zip',
         ['elife-19405.pdf', 'elife-19405.xml']),
        ('tests/test_data/pmc/elife-05-19405.zip', 19405, 'HEFCE', 'elife-05-19405.zip',
         ['elife-19405.pdf', 'elife-19405.xml', 'elife-19405-inf1.tif', 'elife-19405-fig1.tif']),
    )
    @unpack
    def test_move_or_repackage_pmc_zip(self, input_zip_file_path, doi_id, workflow,
                                       expected_zip_file, expected_zip_file_contents):
        # create activity directories
        self.activity.create_activity_directories()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.INPUT_DIR, input_zip_file_path.split('/')[-1])
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        # call the activity function
        self.activity.move_or_repackage_pmc_zip(doi_id, workflow)
        # confirm the output
        ftp_outbox_dir = os.path.join(self.activity.get_tmp_dir(), self.activity.FTP_TO_SOMEWHERE_DIR)
        self.assertTrue(expected_zip_file in os.listdir(ftp_outbox_dir))
        with zipfile.ZipFile(os.path.join(ftp_outbox_dir, expected_zip_file)) as zip_file:
            self.assertEqual(zip_file.namelist(), expected_zip_file_contents)


if __name__ == '__main__':
    unittest.main()
