import unittest
import logging
import requests
import shimmy
from shimmy import Shimmy
import activity
#from .activity import classes_mock
from mock import Mock, patch
from pprint import pprint
from ddt import ddt, data, unpack

class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.reason = 'This is fake'
        self.text = 'This is a fake response text'

    def json(self):
        return {}

@ddt
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

    @data(({}, {}))
    @unpack
    def test_empty_empty_extract_update_date(self, passthrough_json, response_json):
        update_date = self.shimmy.extract_update_date(passthrough_json, response_json)
        self.assertEqual(update_date, None)

    @data(({'update_date': u'2012-12-13T00:00:00Z'}, {}))
    @unpack
    def test_passthrough_extract_update_date(self, passthrough_json, response_json):
        update_date = self.shimmy.extract_update_date(passthrough_json, response_json)
        self.assertEqual(update_date, '2012-12-13T00:00:00Z')

    @data(({}, {'update':'2012-12-13T00:00:00+00:00'}))
    @unpack
    def test_response_extract_update_date(self, passthrough_json, response_json):
        update_date = self.shimmy.extract_update_date(passthrough_json, response_json)
        self.assertEqual(update_date, '2012-12-13T00:00:00Z')

    def _post_some_eif(self):
        return lambda: self.shimmy.post_eif(
            '{"field":"value"}',
            None,
            None,
            { },
            self.queue
        )
        

