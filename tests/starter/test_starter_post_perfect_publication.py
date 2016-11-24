import unittest
from starter.starter_PostPerfectPublication import starter_PostPerfectPublication
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from tests.classes_mock import FakeBotoConnection

class TestStarterPostPerfectPublication(unittest.TestCase):
    def setUp(self):
        self.stater_post_perfect_publication = starter_PostPerfectPublication()

    def test_post_perfect_publication_starter_no_article(self):
        self.assertRaises(NullRequiredDataException, self.stater_post_perfect_publication.start,
                          settings=settings_mock, info=test_data.data_invalid_lax)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_post_perfect_publication_starter_(self, fake_boto_conn, fake_logger):
        fake_boto_conn.return_value = FakeBotoConnection()
        self.stater_post_perfect_publication.start(info=test_data.data_error_lax, settings=settings_mock)


if __name__ == '__main__':
    unittest.main()
