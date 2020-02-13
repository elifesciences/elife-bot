import unittest
from collections import OrderedDict
from mock import patch
from requests.exceptions import HTTPError
from provider import requests_provider
from provider.utils import bytes_decode
from tests.activity.classes_mock import FakeLogger, FakeResponse


class TestRequestsProvider(unittest.TestCase):

    def test_jats_post_payload(self):
        content_type = 'decision'
        doi = '10.7554/eLife.00666'
        content = {}
        api_key = 'key'
        expected = OrderedDict([
            ('apiKey', api_key),
            ('accountKey', 1),
            ('doi', doi),
            ('type', content_type),
            ('content', {})
        ])
        result = requests_provider.jats_post_payload(content_type, doi, content, api_key)
        self.assertEqual(result, expected)


class TestRequestsProviderPostAs(unittest.TestCase):

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_get_as_params(self, fake_connection):
        """"test get data as params only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url + '?type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        expected_body = None
        # populate the fake request
        resp = requests_provider.get_as_params(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_params(self, fake_connection):
        """"test posting data as params only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url + '?type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        expected_body = None
        # populate the fake request
        resp = requests_provider.post_as_params(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_data(self, fake_connection):
        """"test posting data as data only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url
        expected_body = 'type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        # populate the fake request
        resp = requests_provider.post_as_data(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_json(self, fake_connection):
        """test posting data as data only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url
        expected_body = '{"type": "digest", "content": "<p>\\"98%\\"\\u03b2</p>"}'
        # populate the fake request
        resp = requests_provider.post_as_json(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(bytes_decode(resp.request.body), expected_body)


class TestRequestsProviderPost(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    @patch('requests.post')
    def test_post_to_endpoint_200(self, post_mock):
        post_mock.return_value = FakeResponse(200, {})
        url = ''
        payload = {}
        identifier = 'test'
        requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        # assert no errors or exceptions in log
        self.assertEqual(self.fake_logger.logerror, 'First logger error')
        self.assertEqual(self.fake_logger.logexception, 'First logger exception')

    @patch('requests.post')
    def test_post_to_endpoint_404(self, post_mock):
        post_mock.return_value = FakeResponse(404, {})
        url = ''
        payload = {}
        identifier = 'test'
        with self.assertRaises(HTTPError):
            requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertEqual(
            self.fake_logger.logerror,
            'Error posting test to endpoint : status_code: 404\nresponse: None\npayload: {}')

    @patch('requests.post')
    def test_post_to_endpoint_exception(self, post_mock):
        post_mock.side_effect = Exception('Unknown exception')
        url = ''
        payload = {}
        identifier = 'test'
        with self.assertRaises(Exception):
            requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertEqual(
            self.fake_logger.logexception,
            'Exception in post_to_endpoint')
