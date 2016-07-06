import unittest
import logging
import requests
import shimmy
from shimmy import Shimmy
import activity
#from .activity import classes_mock
from mock import Mock, patch
from pprint import pprint

class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.reason = 'This is fake'

    def json(self):
        return {}

class tests_Shimmy(unittest.TestCase):
    def setUp(self):
        settings = Mock()
        settings.drupal_EIF_endpoint = 'http://example.com/article.json'
        self.shimmy = Shimmy(settings)
        self.queue = Mock()

    @patch.object(logging, 'error')
    @patch.object(requests, 'post')
    def test_200_response_code(self, post, error):
        post.return_value = FakeResponse(200)
        attempt = self._post_some_eif()
        attempt()
        error.assert_not_called()
        assert self.queue.write.called

    @patch.object(logging, 'error')
    @patch.object(requests, 'post')
    def test_429_response_code(self, post, error):
        post.return_value = FakeResponse(429)
        attempt = self._post_some_eif()
        self.assertRaises(shimmy.ShortRetryException, attempt)
        error.assert_not_called()
        self.queue.write.assert_not_called()

    @patch.object(logging, 'error')
    @patch.object(requests, 'post')
    def test_500_response_code(self, post, error):
        post.return_value = FakeResponse(500)
        attempt = self._post_some_eif()
        attempt()
        assert(error.called)
        self.queue.write.assert_not_called()

    def _post_some_eif(self):
        return lambda: self.shimmy.post_eif(
            '{"field":"value"}',
            None,
            None,
            { },
            self.queue
        )
