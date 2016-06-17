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


class tests_PostEIFBridge(unittest.TestCase):
    def setUp(self):
        self.activity_PreparePostEIF = activity_PreparePostEIF(settings_mock, None, None, None, None)

    def test_activity(self):
        #TODO: mock
        #success = self.activity_PreparePostEIF.do_activity(data.PostEIFBridge_data(True))
        #self.assertEqual(True, success)
        pass

if __name__ == '__main__':
    unittest.main()
