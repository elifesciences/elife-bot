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


    @patch.object(activity_FTPArticle, "repackage_archive_zip_to_pmc_zip")
    @patch.object(activity_FTPArticle, "download_archive_zip_from_s3")
    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch.object(activity_FTPArticle, "ftp_to_endpoint")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', True, None, 'hefce_ftp.localhost', 'hefce_sftp.localhost', True),
        ('Cengage', True, None, 'cengage.localhost', None, True),
        ('GoOA', True, None, 'gooa.localhost', None, True),
        ('Scopus', True, None, 'scopus_ftp.localhost', 'scopus_sftp.localhost', True),
        ('WoS', True, None, 'wos.localhost', None, True),
        ('CNPIEC', True, None, 'cnpiec.localhost', None, True),
        ('CNPIEC', False, True, 'cnpiec.localhost', None, True),
        ('CNKI', True, None, 'cnki.localhost', None, True),
        ('CNKI', False, True, 'cnki.localhost', None, True),
    )
    @unpack
    def test_do_activity(self, workflow, pmc_zip_return_value, archive_zip_return_value,
                         expected_ftp_uri, expected_sftp_uri, expected_result,
                         fake_sftp_to_endpoint, fake_ftp_to_endpoint,
                         fake_download_pmc_zip_from_s3, fake_download_archive_zip_from_s3,
                         fake_repackage_pmc_zip):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp_to_endpoint = MagicMock()
        fake_download_pmc_zip_from_s3.return_value = pmc_zip_return_value
        fake_download_archive_zip_from_s3.return_value = archive_zip_return_value
        fake_repackage_pmc_zip.return_value = True
        activity_data = {
            'data': {
                'elife_id': '19405',
                'workflow': workflow
            }
        }
        self.assertEqual(self.activity.do_activity(activity_data), expected_result)
        self.assertEqual(self.activity.FTP_URI, expected_ftp_uri)
        self.assertEqual(self.activity.SFTP_URI, expected_sftp_uri)


    @patch.object(activity_FTPArticle, "download_archive_zip_from_s3")
    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch.object(activity_FTPArticle, "ftp_to_endpoint")
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', 'non_numeric_raises_exception', False),
    )
    @unpack
    def test_do_activity_failure(self, workflow, elife_id, expected_result,
                                 fake_sftp_to_endpoint, fake_ftp_to_endpoint,
                                 fake_download_pmc_zip_from_s3, fake_download_archive_zip_from_s3):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp_to_endpoint = MagicMock()
        fake_download_pmc_zip_from_s3 = MagicMock()
        fake_download_archive_zip_from_s3.return_value = True
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
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_zip_file_contents))


    def test_repackage_archive_zip_to_pmc_zip(self):
        input_zip_file_path = 'tests/test_data/pmc/elife-19405-vor-v1-20160802113816.zip'
        doi_id = 19405
        zip_renamed_files_dir = os.path.join(self.activity.get_tmp_dir(), self.activity.RENAME_DIR)
        pmc_zip_output_dir = os.path.join(self.activity.get_tmp_dir(), self.activity.INPUT_DIR)
        expected_pmc_zip_file = os.path.join(pmc_zip_output_dir, 'elife-05-19405.zip')
        expected_article_xml_file = os.path.join(zip_renamed_files_dir, 'elife-19405.xml')
        expected_article_xml_string = b'elife-19405.pdf'
        expected_pmc_zip_file_contents = ['elife-19405.pdf', 'elife-19405.xml',
                                          'elife-19405-inf1.tif', 'elife-19405-fig1.tif']
        # create activity directories
        self.activity.create_activity_directories()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.get_tmp_dir(), self.activity.TMP_DIR, input_zip_file_path.split('/')[-1])
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        self.activity.repackage_archive_zip_to_pmc_zip(doi_id)
        # now can check the results
        self.assertTrue(os.path.exists(expected_pmc_zip_file))
        self.assertTrue(os.path.exists(expected_article_xml_file))
        with open(expected_article_xml_file, 'rb') as fp:
            # check for a renamed file in the XML contents
            self.assertTrue(expected_article_xml_string in fp.read())
        with zipfile.ZipFile(expected_pmc_zip_file) as zip_file:
            # check pmc zip file contents
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_pmc_zip_file_contents))



if __name__ == '__main__':
    unittest.main()
