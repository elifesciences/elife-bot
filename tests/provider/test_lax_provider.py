import unittest
import provider.lax_provider as lax_provider
import tests.settings_mock as settings_mock
import base64
import json

from mock import mock, patch

lax_article_versions_response_data = [
                                        {
                                          "status": "poa",
                                          "version": 1,
                                          "published": "2015-11-26T00:00:00Z"
                                        },
                                        {
                                          "status": "poa",
                                          "version": 2,
                                          "published": "2015-11-30T00:00:00Z"
                                        },
                                        {
                                          "status": "vor",
                                          "version": 3,
                                          "published": "2015-12-29T00:00:00Z"
                                        }
                                      ]

class TestLaxProvider(unittest.TestCase):

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(2, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version_no_versions(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(0, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual("1", version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 500, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(None, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_200(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, lax_article_versions_response_data
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual('20151126000000', date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_200_no_versions(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_404(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, lax_article_versions_response_data
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_500(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 500, lax_article_versions_response_data
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.get_xml_file_name')
    def test_prepare_action_message(self, fake_xml_file_name):
        fake_xml_file_name.return_value = "elife-00353-v1.xml"
        message = lax_provider.prepare_action_message(settings_mock,
                                                      "00353", "bb2d37b8-e73c-43b3-a092-d555753316af",
                                                      "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                                      "1", "vor", "", "ingest")
        self.assertIn('token', message)
        del message['token']
        self.assertDictEqual(message, {'action': 'ingest',
                                       'id': '00353',
                                       'location': 'https://s3.amazonaws.com/origin_bucket/00353.1/bb2d37b8-e73c-43b3-a092-d555753316af/elife-00353-v1.xml',
                                       'version': 1,
                                       'force': False})

    def test_lax_token(self):
        token = lax_provider.lax_token("bb2d37b8-e73c-43b3-a092-d555753316af",
                                       "1",
                                       "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                       "vor",
                                       "")

        self.assertEqual(json.loads(base64.decodestring(token)), {"run": "bb2d37b8-e73c-43b3-a092-d555753316af",
                                                                  "version": "1",
                                                                  "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                                                  "eif_location": "",
                                                                  "status": "vor",
                                                                  "force": False})


if __name__ == '__main__':
    unittest.main()
