import unittest
from starter.starter_ProcessArticleZip import starter_ProcessArticleZip
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeBotoConnection
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch


class TestStarterProcessArticleZip(unittest.TestCase):
    def setUp(self):
        self.stater_process_article_zip = starter_ProcessArticleZip()

    def test_process_article_zip_no_article(self):
        self.assertRaises(NullRequiredDataException, self.stater_process_article_zip.start,
                          settings=settings_mock, **test_data.data_invalid_lax)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_process_article_zip_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_process_article_zip.start(settings=settings_mock, **test_data.data_ingested_lax)




if __name__ == '__main__':
    unittest.main()
