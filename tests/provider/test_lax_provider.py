import unittest
import provider.utils as utils
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

    @patch("provider.lax_provider.article_versions")
    def test_article_version_date_by_version_with_preprint(
        self, mock_lax_provider_article_versions
    ):
        response_data = [
            {"status": "preprint"},
            {"version": 1, "versionDate": "2015-11-30T00:00:00Z"},
        ]
        mock_lax_provider_article_versions.return_value = 200, response_data
        result = lax_provider.article_version_date_by_version(
            "08411", "1", settings_mock
        )
        self.assertEqual("2015-11-30T00:00:00Z", result)

    @patch('requests.get')
    def test_article_version_200(self, mock_requests_get):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'versions': [{"status": "preprint"}, {'version': 1}]}
        mock_requests_get.return_value = response
        status_code, versions = lax_provider.article_versions('08411', settings_mock)
        self.assertEqual(status_code, 200)
        self.assertEqual(versions, [{"status": "preprint"}, {'version': 1}])

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

    @patch('requests.get')
    def test_article_json_200(self, mock_requests_get):
        article_json = {"status": "vor"}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = article_json
        mock_requests_get.return_value = response
        status_code, data = lax_provider.article_json("65469", settings_mock)
        self.assertEqual(status_code, 200)
        # data returned will be exactly the value assigned to the mock response
        self.assertEqual(data, article_json)

    @patch("requests.get")
    def test_article_related_200(self, mock_requests_get):
        related_article_json = []
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = related_article_json
        mock_requests_get.return_value = response
        status_code, data = lax_provider.article_related("08411", settings_mock)
        self.assertEqual(status_code, 200)
        self.assertEqual(data, related_article_json)

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
        # add a preprint article, which has no version key, for test coverage
        versions_response_data = [{"status": "preprint"}, expected_data]
        response_data = {'versions': versions_response_data}
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

        self.assertEqual(
            json.loads(utils.base64_decode_string(token)), 
            {
                "run": "bb2d37b8-e73c-43b3-a092-d555753316af",
                "version": "1",
                "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
                "status": "vor",
                "force": False,
                "run_type": None})

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

    @patch("provider.lax_provider.article_related")
    def test_article_retracted_status_no_related(self, mock_article_related):
        related_article_json = []
        mock_article_related.return_value = 200, related_article_json
        retracted_status = lax_provider.article_retracted_status("04132", settings_mock)
        self.assertEqual(retracted_status, False)

    @patch("provider.lax_provider.article_related")
    def test_article_retracted_status_related(self, mock_article_related):
        related_article_json = [
            {
                "status": "vor",
                "id": "65227",
                "version": 1,
                "type": "retraction",
                "doi": "10.7554/eLife.65227",
                "authorLine": "Yang Li et al.",
                "title": (
                    "Retraction: Endocytic recycling and vesicular transport systems "
                    "mediatetranscytosis of Leptospira interrogans across cell monolayer"),
                "published": "2020-12-03T00:00:00Z",
                "versionDate": "2020-12-03T00:00:00Z",
                "volume": 9,
                "elocationId": "e65227",
                "subjects": [
                    {
                        "id": "microbiology-infectious-disease",
                        "name": "Microbiology and Infectious Disease",
                    }
                ],
                "copyright": {
                    "license": "CC-BY-4.0",
                    "holder": "Li et al.",
                    "statement": (
                        'This article is distributed under the terms of the '
                        '<a href="http://creativecommons.org/licenses/by/4.0/">'
                        'Creative Commons Attribution License</a>, which permits '
                        'unrestricted use and redistribution provided that the '
                        'original author and source are credited.'),
                },
                "stage": "published",
                "statusDate": "2020-12-03T00:00:00Z",
            }
        ]
        mock_article_related.return_value = 200, related_article_json
        retracted_status = lax_provider.article_retracted_status("44594", settings_mock)
        self.assertTrue(retracted_status)

    @patch("provider.lax_provider.article_related")
    def test_article_retracted_status_related_insight_only(self, mock_article_related):
        related_article_json = [
            {
                "type":"insight"
            }
        ]
        mock_article_related.return_value = 200, related_article_json
        retracted_status = lax_provider.article_retracted_status("99999", settings_mock)
        self.assertEqual(retracted_status, False)

    @patch("provider.lax_provider.article_related")
    def test_article_retracted_status_404(self, mock_article_related):
        mock_article_related.return_value = 404, None
        retracted_status = lax_provider.article_retracted_status("04132", settings_mock)
        self.assertIsNone(retracted_status)

    @patch("provider.lax_provider.article_versions")
    def test_article_status_version_map(self, mock_lax_provider_article_versions):
        expected = {"poa": [1, 2], "vor": [3]}
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = (
            200, test_data.lax_article_versions_response_data)
        version_status_map = lax_provider.article_status_version_map(article_id, settings_mock)
        self.assertEqual(version_status_map, expected)

    @patch('provider.lax_provider.article_versions')
    def test_article_status_version_map_500(self, mock_lax_provider_article_versions):
        expected = {}
        article_id = '04132'
        mock_lax_provider_article_versions.return_value = 500, []
        version_status_map = lax_provider.article_status_version_map(article_id, settings_mock)
        self.assertEqual(version_status_map, expected)

    @patch('provider.lax_provider.article_status_version_map')
    def test_article_first_by_status_first_vor(self, mock_version_status_map):
        mock_version_status_map.return_value = {"poa": [1, 2], "vor": [3]}
        article_id = '04132'
        version = 3
        status = 'vor'
        expected = True
        first = lax_provider.article_first_by_status(article_id, version, status, settings_mock)
        self.assertEqual(first, expected)

    @patch('provider.lax_provider.article_status_version_map')
    def test_article_first_by_status_first_poa(self, mock_version_status_map):
        mock_version_status_map.return_value = {"poa": [1, 2], "vor": [3]}
        article_id = '04132'
        version = 1
        status = 'poa'
        expected = True
        first = lax_provider.article_first_by_status(article_id, version, status, settings_mock)
        self.assertEqual(first, expected)

    @patch('provider.lax_provider.article_status_version_map')
    def test_article_first_by_status_not_first_vor(self, mock_version_status_map):
        mock_version_status_map.return_value = {"poa": [1, 2], "vor": [4, 3]}
        article_id = '04132'
        version = 4
        status = 'vor'
        expected = False
        first = lax_provider.article_first_by_status(article_id, version, status, settings_mock)
        self.assertEqual(first, expected)

    @patch('provider.lax_provider.article_status_version_map')
    def test_article_first_by_status_not_first_poa(self, mock_version_status_map):
        mock_version_status_map.return_value = {"poa": [1, 2], "vor": [3]}
        article_id = '04132'
        version = 2
        status = 'poa'
        expected = False
        first = lax_provider.article_first_by_status(article_id, version, status, settings_mock)
        self.assertEqual(first, expected)

    @patch('provider.lax_provider.article_status_version_map')
    def test_article_first_by_status_no_vor(self, mock_version_status_map):
        mock_version_status_map.return_value = {"poa": [1, 2]}
        article_id = '04132'
        version = 2
        status = 'vor'
        expected = None
        first = lax_provider.article_first_by_status(article_id, version, status, settings_mock)
        self.assertEqual(first, expected)


if __name__ == '__main__':
    unittest.main()
