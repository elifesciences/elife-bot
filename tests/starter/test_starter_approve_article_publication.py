import unittest
from starter.starter_ApproveArticlePublication import starter_ApproveArticlePublication
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeBotoConnection
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch


class TestStarterApproveArticlePublication(unittest.TestCase):
    def setUp(self):
        self.stater_approve_article_publication = starter_ApproveArticlePublication()

    def test_process_approve_article_publication(self):
        invalid_data = test_data.ApprovePublication_data()
        invalid_data["version"] = None
        self.assertRaises(NullRequiredDataException, self.stater_approve_article_publication.start,
                          settings=settings_mock, **invalid_data)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_approve_article_publication_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_approve_article_publication.start(settings=settings_mock, **test_data.ApprovePublication_data())




if __name__ == '__main__':
    unittest.main()
