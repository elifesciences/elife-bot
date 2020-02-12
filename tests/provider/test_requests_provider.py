import unittest
from collections import OrderedDict
from mock import patch
from provider import requests_provider
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


class TestRequestsProviderPost(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    @patch('requests.post')
    def test_post_to_endpoint_200(self, post_mock):
        post_mock.return_value = FakeResponse(200, {})
        url = ''
        payload = {}
        identifier = 'test'
        result = requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertTrue(result)

    @patch('requests.post')
    def test_post_to_endpoint_404(self, post_mock):
        post_mock.return_value = FakeResponse(404, {})
        url = ''
        payload = {}
        identifier = 'test'
        result = requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertEqual(
            result, 'Error posting test to endpoint : status_code: 404\nresponse: None')
