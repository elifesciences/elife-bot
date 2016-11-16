import unittest
from starter.starter_PostPerfectPublication import starter_PostPerfectPublication
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from testfixtures import LogCapture


class TestStarterPostPerfectPublication(unittest.TestCase):
    def setUp(self):
        self.stater_post_perfect_publication = starter_PostPerfectPublication()

    # def test_post_perfect_publication_starter(self):
    #     self.stater_post_perfect_publication.start(settings=settings_mock, info=test_data.data_published_lax)
    #     self.assertEqual(True, False)

    def test_post_perfect_publication_starter_no_article(self):
        with LogCapture() as l:
            self.stater_post_perfect_publication.start(settings=settings_mock, info=test_data.data_invalid_lax)

        l.check('root', 'ERROR', 'article id is Null. Possible error: '
                                   'Lax did not send back valid data from ingest.')


if __name__ == '__main__':
    unittest.main()
