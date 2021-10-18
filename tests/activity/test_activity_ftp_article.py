import unittest
import shutil
import os
import zipfile
from mock import patch, MagicMock
from ddt import ddt, data, unpack
import activity.activity_FTPArticle as activity_module
from activity.activity_FTPArticle import activity_FTPArticle
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeFTP, FakeLogger


@ddt
class TestFTPArticle(unittest.TestCase):

    def setUp(self):
        self.activity = activity_FTPArticle(settings_mock, FakeLogger(), None, None, None)

    def tearDown(self):
        self.activity.clean_tmp_dir()

    @patch.object(activity_FTPArticle, "repackage_archive_zip_to_pmc_zip")
    @patch.object(activity_FTPArticle, "download_archive_zip_from_s3")
    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch('activity.activity_FTPArticle.FTP')
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', True, None, 'hefce_ftp.localhost', 'hefce_sftp.localhost', True),
        ('Cengage', True, None, 'cengage.localhost', None, True),
        ('GoOA', True, None, 'gooa.localhost', None, True),
        ('WoS', True, None, 'wos.localhost', None, True),
        ('CNPIEC', True, None, 'cnpiec.localhost', None, True),
        ('CNPIEC', False, True, 'cnpiec.localhost', None, True),
        ('CNKI', True, None, 'cnki.localhost', None, True),
        ('CNKI', False, True, 'cnki.localhost', None, True),
        ('CLOCKSS', True, None, 'clockss.localhost', None, True),
        ('CLOCKSS', False, True, 'clockss.localhost', None, True),
        ('OVID', False, True, 'ovid.localhost', None, True),
        ('Zendy', False, True, None, 'zendy.localhost', True),
    )
    @unpack
    def test_do_activity(self, workflow, pmc_zip_return_value, archive_zip_return_value,
                         expected_ftp_uri, expected_sftp_uri, expected_result,
                         fake_sftp_to_endpoint, fake_ftp,
                         fake_download_pmc_zip_from_s3, fake_download_archive_zip_from_s3,
                         fake_repackage_pmc_zip):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp.return_value = FakeFTP()
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

    @patch.object(activity_FTPArticle, "download_pmc_zip_from_s3")
    @patch('activity.activity_FTPArticle.FTP')
    @patch.object(activity_FTPArticle, "sftp_to_endpoint")
    @data(
        ('HEFCE', 'non_numeric_raises_exception', False),
    )
    @unpack
    def test_do_activity_failure(self, workflow, elife_id, expected_result,
                                 fake_sftp_to_endpoint, fake_ftp,
                                 fake_download_pmc_zip_from_s3):
        fake_sftp_to_endpoint = MagicMock()
        fake_ftp.return_value = FakeFTP()
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
        ('tests/test_data/pmc/elife-05-19405.zip', 19405, 'CNKI', 'elife-19405-xml.zip',
         ['elife-19405.xml']),
    )
    @unpack
    def test_move_or_repackage_pmc_zip(self, input_zip_file_path, doi_id, workflow,
                                       expected_zip_file, expected_zip_file_contents):
        # create activity directories
        self.activity.make_activity_directories()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"), input_zip_file_path.split('/')[-1])
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        # call the activity function
        self.activity.move_or_repackage_pmc_zip(doi_id, workflow)
        # confirm the output
        ftp_outbox_dir = self.activity.directories.get("FTP_TO_SOMEWHERE_DIR")
        self.assertTrue(expected_zip_file in os.listdir(ftp_outbox_dir))
        with zipfile.ZipFile(os.path.join(ftp_outbox_dir, expected_zip_file)) as zip_file:
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_zip_file_contents))

    def test_repackage_archive_zip_to_pmc_zip(self):
        input_zip_file_path = 'tests/test_data/pmc/elife-19405-vor-v1-20160802113816.zip'
        doi_id = 19405
        # create activity directories
        self.activity.make_activity_directories()
        zip_renamed_files_dir = self.activity.directories.get("RENAME_DIR")
        pmc_zip_output_dir = self.activity.directories.get("INPUT_DIR")
        expected_pmc_zip_file = os.path.join(pmc_zip_output_dir, 'elife-05-19405.zip')
        expected_article_xml_file = os.path.join(zip_renamed_files_dir, 'elife-19405.xml')
        expected_article_xml_string = b'elife-19405.pdf'
        expected_pmc_zip_file_contents = ['elife-19405.pdf', 'elife-19405.xml',
                                          'elife-19405-inf1.tif', 'elife-19405-fig1.tif']
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            self.activity.directories.get("TMP_DIR"), input_zip_file_path.split('/')[-1])
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        self.activity.repackage_archive_zip_to_pmc_zip(doi_id)
        # now can check the results
        self.assertTrue(os.path.exists(expected_pmc_zip_file))
        self.assertTrue(os.path.exists(expected_article_xml_file))
        with open(expected_article_xml_file, 'rb') as open_file:
            # check for a renamed file in the XML contents
            self.assertTrue(expected_article_xml_string in open_file.read())
        with zipfile.ZipFile(expected_pmc_zip_file) as zip_file:
            # check pmc zip file contents
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_pmc_zip_file_contents))


class TestFTPArticleFTPToEndpoint(unittest.TestCase):

    def setUp(self):
        self.activity = activity_FTPArticle(settings_mock, FakeLogger(), None, None, None)
        self.activity.FTP_URI = "ftp.example.org"
        self.activity.FTP_CWD = "folder"
        self.uploadfiles = ["zipfile.zip"]
        self.sub_dir_list = ["subfolder", "subsubfolder"]

    @patch.object(FakeFTP, 'ftp_connect')
    @patch('activity.activity_FTPArticle.FTP')
    def test_ftp_connect_exception(self, fake_ftp, fake_ftp_connect):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_connect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles)
        self.assertEqual(
            self.activity.logger.logexception,
            'Exception connecting to FTP server ftp.example.org: An exception')

    @patch.object(FakeFTP, 'ftp_upload')
    @patch('activity.activity_FTPArticle.FTP')
    def test_ftp_upload_exception(self, fake_ftp, fake_ftp_upload):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_upload.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles, self.sub_dir_list)
        self.assertEqual(
            self.activity.logger.logexception,
            'Exception in uploading file zipfile.zip by FTP in FTPArticle: An exception')

    @patch.object(FakeFTP, 'ftp_disconnect')
    @patch('activity.activity_FTPArticle.FTP')
    def test_ftp_disconnect_exception(self, fake_ftp, fake_ftp_disconnect):
        fake_ftp.return_value = FakeFTP()
        fake_ftp_disconnect.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.activity.ftp_to_endpoint(self.uploadfiles)
        self.assertEqual(
            self.activity.logger.logexception,
            'Exception disconnecting from FTP server ftp.example.org: An exception')


@ddt
class TestZipFileSuffix(unittest.TestCase):

    @data(
        (['xml', 'pdf'], '-xml-pdf.zip'),
        (['xml'], '-xml.zip'),
    )
    @unpack
    def test_zip_file_suffix(self, file_types, expected):
        self.assertEqual(activity_module.zip_file_suffix(file_types), expected)


@ddt
class TestNewZipFileName(unittest.TestCase):

    @data(
        (666, 'elife-', '-xml-pdf.zip', 'elife-00666-xml-pdf.zip'),

    )
    @unpack
    def test_zip_file_suffix(self, doi_id, prefix, suffix, expected):
        self.assertEqual(activity_module.new_zip_file_name(doi_id, prefix, suffix), expected)


@ddt
class TestFileTypeMatches(unittest.TestCase):

    @data(
        (['xml', 'pdf'], ['/*.xml', '/*.pdf']),
        (['xml'], ['/*.xml']),
    )
    @unpack
    def test_file_type_matches(self, file_types, expected):
        self.assertEqual(activity_module.file_type_matches(file_types), expected)


if __name__ == '__main__':
    unittest.main()
