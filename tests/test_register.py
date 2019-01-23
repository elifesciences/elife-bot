import unittest
from mock import patch
from testfixtures import TempDirectory
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeSQSConn, FakeSQSQueue
import register


class TestRegister(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch('boto.sqs.connection.SQSConnection.get_queue')
    @patch('boto.sqs.connect_to_region')
    @patch('boto.swf.layer1.Layer1')
    def test_start(self, fake_layer, fake_sqs_conn, mock_queue):
        directory = TempDirectory()
        fake_sqs_conn.return_value = FakeSQSConn(directory)
        mock_queue.return_value = FakeSQSQueue(directory)
        fake_layer.return_value = FakeLayer1()
        self.assertIsNone(register.start(settings_mock))
