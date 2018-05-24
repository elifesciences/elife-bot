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
        fastly_provider.purge('10627', settings_mock)

    @patch('requests.post')
    def test_purge_failure(self, post_mock):
        response = Response()
        response.status_code = 500
        post_mock.return_value = response
        self.assertRaises(HTTPError, lambda: fastly_provider.purge('10627', settings_mock))
