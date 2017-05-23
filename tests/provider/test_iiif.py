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

    @patch('requests.head')
    def test_try_endpoint_retry(self, request_mock):
        iterable = (ObjectView({'status_code': 504}), ObjectView({'status_code': 200}))
        request_mock.side_effect = iterable
        fake_logger = FakeLogger()
        success, test_endpoint = iiif.try_endpoint("test_endpoint", fake_logger)

        self.assertEqual(success, True)
        self.assertEqual(test_endpoint, "test_endpoint")

    @patch('requests.head')
    def test_try_endpoint_error(self, request_mock):
        iterable = (ObjectView({'status_code': 504}), ObjectView({'status_code': 500}))
        request_mock.side_effect = iterable
        fake_logger = FakeLogger()
        success, test_endpoint = iiif.try_endpoint("test_endpoint", fake_logger)

        self.assertEqual(success, False)
        self.assertEqual(test_endpoint, "test_endpoint")


if __name__ == '__main__':
    unittest.main()
