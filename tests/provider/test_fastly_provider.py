import unittest
from mock import mock, patch
from provider import fastly_provider
from tests import settings_mock
from requests.models import Response
from requests.exceptions import HTTPError

class TestFastlyProvider(unittest.TestCase):
    @patch('requests.post')
    def test_purge(self, post_mock):
        response = Response()
        response.status_code = 200
        post_mock.return_value = response
        fastly_provider.purge('10627', '1', settings_mock)

    @patch('requests.post')
    def test_purge_various_keys(self, post_mock):
        response = Response()
        response.status_code = 200
        post_mock.return_value = response
        fastly_provider.purge('10627', '1', settings_mock)
        self.assertEqual(
            [c[1][0] for c in post_mock.mock_calls],
            [
                'https://api.fastly.com/service/3M35rb7puabccOLrFFxy2/purge/articles/10627v1',
                'https://api.fastly.com/service/3M35rb7puabccOLrFFxy2/purge/articles/10627/videos',
            ]
        )

    @patch('requests.post')
    def test_purge_failure(self, post_mock):
        response = Response()
        response.status_code = 500
        post_mock.return_value = response
        self.assertRaises(HTTPError, lambda: fastly_provider.purge('10627', '1', settings_mock))
