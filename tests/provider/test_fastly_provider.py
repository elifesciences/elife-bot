import unittest
from mock import mock, patch
from provider import fastly_provider
from tests import settings_mock
from requests.models import Response
from requests.exceptions import HTTPError

class TestFastlyProvider(unittest.TestCase):
    @patch('requests.post')
    def test_purge(self, post_mock):
        self._allow_call(post_mock)
        fastly_provider.purge('10627', '1', settings_mock)

    @patch('requests.post')
    def test_purge_various_keys(self, post_mock):
        self._allow_call(post_mock)
        fastly_provider.purge('10627', '1', settings_mock)
        self.assertEqual(
            [c[1][0] for c in post_mock.mock_calls],
            [
                'https://api.fastly.com/service/3M35rb7puabccOLrFFxy2/purge/articles/10627v1',
                'https://api.fastly.com/service/3M35rb7puabccOLrFFxy2/purge/articles/10627/videos',
            ]
        )

    @patch('requests.post')
    def test_purge_return_responses(self, post_mock):
        self._allow_call(post_mock)
        responses = fastly_provider.purge('10627', '1', settings_mock)
        self.assertIsInstance(responses[0], Response)
        self.assertEqual(200, responses[0].status_code)

    @patch('requests.post')
    def test_purge_failure(self, post_mock):
        self._allow_call(post_mock, status_code=500)
        self.assertRaises(HTTPError, lambda: fastly_provider.purge('10627', '1', settings_mock))

    def _allow_call(self, post_mock, status_code=200):
        response = Response()
        response.status_code = status_code
        post_mock.return_value = response

