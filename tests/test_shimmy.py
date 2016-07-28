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
        self.logger = Mock()
        self.shimmy = Shimmy(settings, self.logger)
        self.queue = Mock()

    @patch.object(requests, 'post')
    def test_200_response_code(self, post):
        post.return_value = FakeResponse(200)
        attempt = self._post_some_eif()
        attempt()
        self.logger.error.assert_not_called()
        assert self.queue.write.called

    @patch.object(requests, 'post')
    def test_429_response_code(self, post):
        post.return_value = FakeResponse(429)
        attempt = self._post_some_eif()
        self.assertRaises(shimmy.ShortRetryException, attempt)
        self.logger.error.assert_not_called()
        self.queue.write.assert_not_called()

    @patch.object(requests, 'post')
    def test_500_response_code(self, post):
        post.return_value = FakeResponse(500)
        attempt = self._post_some_eif()
        attempt()
        self.logger.error.assert_called_with('Data sent (first 500 characters): %s', '{"field":"value"}')
        self.queue.write.assert_not_called()

    @data(
        ({}, {}, None),
        ({'update_date': u'2012-12-13T00:00:00Z'}, {}, '2012-12-13T00:00:00Z'),
        ({}, {'update':'2012-12-13T00:00:00+00:00'}, '2012-12-13T00:00:00Z'),
        ({}, {'update':'not_a_date'}, None),
    )
    @unpack
    def test_extract_update_date(self, passthrough_json, response_json, update_date):
        update_date_extracted = self.shimmy.extract_update_date(passthrough_json, response_json)
        self.assertEqual(update_date, update_date_extracted)


    def _post_some_eif(self):
        return lambda: self.shimmy.post_eif(
            '{"field":"value"}',
            None,
            None,
            { },
            self.queue
        )
        

