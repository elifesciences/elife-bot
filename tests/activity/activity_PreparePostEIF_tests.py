import unittest
from activity.activity_PreparePostEIF import activity_PreparePostEIF
import settings_mock
import test_activity_data as data
from mock import mock, patch
from classes_mock import FakeSQSConn
from classes_mock import FakeSQSMessage
from classes_mock import FakeSQSQueue
import classes_mock
from testfixtures import TempDirectory
import json
import base64
import settings


class tests_PostEIFBridge(unittest.TestCase):
    def setUp(self):
        self.activity_PreparePostEIF = activity_PreparePostEIF(settings, None, None, None, None)

    def test_activity(self):

        success = self.activity_PreparePostEIF.do_activity(data.PostEIFBridge_data(True))
        self.assertEqual(True, success)

if __name__ == '__main__':
    unittest.main()
