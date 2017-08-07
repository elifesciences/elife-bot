import unittest
from mock import mock, patch
from provider.iiif import ShortRetryException
import provider.iiif as iiif

class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d

class FakeLogger:
    def __init__(self):
        self.logdebug = "First logger debug"
        self.loginfo = "First logger info"
        self.logexception = "First logger exception"
        self.logerror = "First logger error"
    def debug(self, msg, *args, **kwargs):
        self.logdebug =  msg
    def info(self, msg, *args, **kwargs):
        self.loginfo = msg
    def exception(self, msg, *args, **kwargs):
        self.logexception = msg
    def error(self, msg, *args, **kwargs):
        self.logerror = msg

class TestIiif(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    @patch('requests.head')
    def test_try_endpoint_ok(self, request_mock):
        self._given_responses(request_mock, 200)
        success, test_endpoint = iiif.try_endpoint("test_endpoint", self.fake_logger)
        self.assertEqual(success, True)
        self.assertEqual(test_endpoint, "test_endpoint")

    @patch('requests.head')
    def test_try_endpoint_error(self, request_mock):
        self._given_responses(request_mock, 500)
        success, test_endpoint = iiif.try_endpoint("test_endpoint", self.fake_logger)
        self.assertEqual(success, False)

    @patch('requests.head')
    def test_try_endpoint_retry_of_generic_timeout(self, request_mock):
        self._given_responses(request_mock, 504, 200)
        success, test_endpoint = iiif.try_endpoint("test_endpoint", self.fake_logger)
        self.assertEqual(success, True)

    # Loris exposes 404 on unretrievable images, at this time
    # even if the original error is a 500
    @patch('requests.head')
    def test_try_endpoint_retry_of_not_retrievable_image_source(self, request_mock):
        self._given_responses(request_mock, 404, 200)
        success, test_endpoint = iiif.try_endpoint("test_endpoint", self.fake_logger)
        self.assertEqual(success, True)

    @patch('requests.head')
    def test_try_endpoint_error_on_only_retry(self, request_mock):
        self._given_responses(request_mock, 504, 500)
        success, test_endpoint = iiif.try_endpoint("test_endpoint", self.fake_logger)
        self.assertEqual(success, False)

    def _given_responses(self, request_mock, *status_codes):
        request_mock.side_effect = [ObjectView({'status_code': code}) for code in status_codes]


if __name__ == '__main__':
    unittest.main()
