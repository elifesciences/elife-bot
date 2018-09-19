import unittest
import provider.lax_provider as lax_provider
import tests.settings_mock as settings_mock
import base64
import json
import tests.test_data as test_data
from provider.lax_provider import ErrorCallingLaxException

from mock import mock, patch, MagicMock
from ddt import ddt, data, unpack

@ddt
class TestLaxProvider(unittest.TestCase):

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version_200(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(3, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version_no_versions(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(0, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version_404(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, None
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual("1", version)

    @patch('provider.lax_provider.article_versions')
    def test_article_next_version_no_versions(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        version = lax_provider.article_next_version('08411', settings_mock)
        self.assertEqual("1", version)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_200(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual('20151126000000', date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_200_no_versions(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_404(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, None
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_publication_date_500(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 500, None
        date_str = lax_provider.article_publication_date('08411', settings_mock)
        self.assertEqual(None, date_str)

    @patch('provider.lax_provider.article_versions')
    def test_article_version_date_by_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        result = lax_provider.article_version_date_by_version('08411', "2", settings_mock)
        self.assertEqual("2015-11-30T00:00:00Z", result)

    @patch('requests.get')
    def test_article_version_200(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'versions': [{'version': 1}]}
        mock_requests_get.return_value = response
        status_code, versions = lax_provider.article_versions('08411', settings_mock)
        self.assertEqual(status_code, 200)
        self.assertEqual(versions, [{'version': 1}])

    @patch('requests.get')
    def test_article_version_404(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 404
        mock_requests_get.return_value = response
        status_code, versions = lax_provider.article_versions('08411', settings_mock)
        self.assertEqual(status_code, 404)
        self.assertIsNone(versions)

    @patch('requests.get')
    def test_article_version_500(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 500
        mock_requests_get.return_value = response
        self.assertRaises(ErrorCallingLaxException, lax_provider.article_highest_version, '08411', settings_mock)

    def test_lax_auth_header_none(self):
        expected = {}
        self.assertEqual(lax_provider.lax_auth_header(None), expected)

    def test_lax_auth_header_true(self):
        auth_key = 'a_key'
        expected = {'Authorization': 'a_key'}
        self.assertEqual(lax_provider.lax_auth_header(auth_key), expected)

    def test_lax_auth_key_false(self):
        expected = 'public'
        self.assertEqual(lax_provider.lax_auth_key(settings_mock), expected)

    def test_lax_auth_key_true(self):
        expected = 'an_auth_key'
        self.assertEqual(lax_provider.lax_auth_key(settings_mock, True), expected)

    @patch('requests.get')
    def test_article_snippet_200_auth(self, mock_requests_get):
        expected_data = {'version': 1, 'type': 'research-article'}
        response_data = {'versions': [expected_data]}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = response_data
        mock_requests_get.return_value = response
        data = lax_provider.article_snippet('08411', 1, settings_mock, True)
        self.assertEqual(data, expected_data)

    @patch('requests.get')
    def test_article_snippet_403(self, mock_requests_get):
        "scenario where the request is not authorized"
        response = MagicMock()
        response.status_code = 403
        mock_requests_get.return_value = response
        self.assertRaises(ErrorCallingLaxException, lax_provider.article_snippet,
                          '08411', 1, settings_mock, True)

    # endpoint currently not available
    # @patch('provider.lax_provider.article_version')
    # def test_article_publication_date_by_version_id_version(self, mock_lax_provider_article_version):
    #     mock_lax_provider_article_version.return_value = 200, test_data.lax_article_by_version_response_data_incomplete
    #     result = lax_provider.article_version_date('08411', "2", settings_mock)
    #     self.assertEqual("2016-11-11T17:48:41Z", result)

    def test_poa_vor_status_both_true(self):
        exp_poa_status, exp_vor_status = lax_provider.poa_vor_status(test_data.lax_article_versions_response_data)
        self.assertEqual(True, exp_poa_status)
        self.assertEqual(True, exp_vor_status)

    def test_poa_vor_status_both_none(self):
        exp_poa_status, exp_vor_status = lax_provider.poa_vor_status([])
        self.assertEqual(None, exp_poa_status)
        self.assertEqual(None, exp_vor_status)

    def test_poa_vor_status_not_found(self):
        data = None
        exp_poa_status, exp_vor_status = lax_provider.poa_vor_status(data)
        self.assertEqual(None, exp_poa_status)
        self.assertEqual(None, exp_vor_status)

    def test_poa_vor_status_blank_version(self):
        data = [{},{"status":"poa","version":1}]
        exp_poa_status, exp_vor_status = lax_provider.poa_vor_status(data)
        self.assertEqual(True, exp_poa_status)
        self.assertEqual(None, exp_vor_status)

    @patch('provider.lax_provider.get_xml_file_name')
    def test_prepare_action_message(self, fake_xml_file_name):
        fake_xml_file_name.return_value = "elife-00353-v1.xml"
        message = lax_provider.prepare_action_message(settings_mock,
                                                      "00353", "bb2d37b8-e73c-43b3-a092-d555753316af",
                                                      "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                                      "1", "vor", "ingest")
        self.assertIn('token', message)
        del message['token']
        self.assertDictEqual(message, {'action': 'ingest',
                                       'id': '00353',
                                       'location': 'https://s3-external-1.amazonaws.com/origin_bucket/00353.1/bb2d37b8-e73c-43b3-a092-d555753316af/elife-00353-v1.xml',
                                       'version': 1,
                                       'force': False})

    def test_lax_token(self):
        token = lax_provider.lax_token("bb2d37b8-e73c-43b3-a092-d555753316af",
                                       "1",
                                       "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                       "vor")

        self.assertEqual(json.loads(base64.decodestring(token)), {"run": "bb2d37b8-e73c-43b3-a092-d555753316af",
                                                                  "version": "1",
                                                                  "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                                                                  "status": "vor",
                                                                  "force": False})

    @patch('provider.lax_provider.article_versions')
    def test_was_ever_poa_was_poa(self, mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        
        result = lax_provider.was_ever_poa(article_id, settings_mock)
        self.assertEqual(result, True)

    @patch('provider.lax_provider.article_versions')
    def test_was_ever_poa_was_not_poa(self, mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 200, [test_data.lax_article_by_version_response_data_incomplete]
        result = lax_provider.was_ever_poa(article_id, settings_mock)
        self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_was_ever_poa_was_not_poa_blank(self, mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 200, []
        result = lax_provider.was_ever_poa(article_id, settings_mock)
        self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_was_ever_poa_was_not_poa_500(self, mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 500, []
        result = lax_provider.was_ever_poa(article_id, settings_mock)
        self.assertEqual(result, None)

    @patch('provider.lax_provider.article_versions')
    @data(
        (True, True, True),
        (True, False, False),
        (True, None, False),
        (False, True, True),
        (False, False, True),
        (False, None, False),
    )
    @unpack
    def test_published_considering_poa_status(self, is_poa, was_ever_poa, expected_return_value,
                                              mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        published = lax_provider.published_considering_poa_status(article_id, settings_mock,
                                                                  is_poa, was_ever_poa)
        self.assertEqual(published, expected_return_value)

    @patch('provider.lax_provider.article_versions')
    @data(
        (True, True, False),
        (True, False, False),
        (True, None, False),
        (False, True, False),
        (False, False, False),
        (False, None, False),
    )
    @unpack
    def test_published_considering_poa_status_500(self, is_poa, was_ever_poa, expected_return_value,
                                              mock_lax_provider_article_versions):
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 500, []
        published = lax_provider.published_considering_poa_status(article_id, settings_mock,
                                                                  is_poa, was_ever_poa)
        self.assertEqual(published, expected_return_value)


if __name__ == '__main__':
    unittest.main()
