import unittest
from starter.starter_ArticleInformationSupplier import starter_ArticleInformationSupplier
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeBotoConnection
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch

data = {
    'eif_location': '00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251/elife-00353-v1.json',
    'eif_bucket':  'jen-elife-publishing-eif',
    'article_id': u'00353',
    'version': u'1',
    'run': u'cf9c7e86-7355-4bb4-b48e-0bc284221251',
    'article_path': 'content/1/e00353v1',
    'published': False,
    'expanded_folder': u'00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251',
    'status': u'vor',
    'update_date': "2012-12-13T00:00:00Z"
}

class TestStarterArticleInformationSupplier(unittest.TestCase):
    def setUp(self):
        self.stater_article_information_supplier = starter_ArticleInformationSupplier()

    def test_article_information_supplier_no_article(self):
        data_invalid = data.copy()
        data_invalid["article_id"] = None
        self.assertRaises(NullRequiredDataException, self.stater_article_information_supplier.start,
                          settings=settings_mock, **data_invalid)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_process_article_zip_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_article_information_supplier.start(settings=settings_mock, **data)




if __name__ == '__main__':
    unittest.main()
