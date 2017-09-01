import unittest
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




if __name__ == '__main__':
    unittest.main()
