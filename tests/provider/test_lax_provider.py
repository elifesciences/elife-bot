import unittest
import provider.lax_provider as lax_provider
import tests.settings_mock as settings_mock
import tests.activity.test_provider_data as test_data

from mock import mock, patch


class TestLaxProvider(unittest.TestCase):

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual("2", version)


if __name__ == '__main__':
    unittest.main()
