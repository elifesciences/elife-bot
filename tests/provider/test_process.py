import unittest
from mock import patch
from provider import process
from provider.process import Flag
from tests.classes_mock import FakeFlag


class TestObject:
    "object for testing work() process"

    def work(self, flag):
        pass


class TestExpandArticle(unittest.TestCase):
    def test_flag_starts_green_and_become_red_upon_termination_signal(self):
        "test the Flag object"
        flag = Flag()
        self.assertTrue(flag.green())
        self.assertFalse(flag.red())
        flag.stop_process()
        self.assertFalse(flag.green())
        self.assertTrue(flag.red())


class TestMonitorInterrupt(unittest.TestCase):
    def test_monitor_interrupt(self):
        "test when flag goes red"
        mock_flag = FakeFlag(0.01)
        # invoke green() once so the next attempt will be red
        mock_flag.green()
        test_object = TestObject()
        process.monitor_interrupt(lambda flag: test_object.work(mock_flag))
        self.assertFalse(mock_flag.green_value)

    @patch.object(TestObject, "work")
    def test_monitor_interrupt_exception(self, fake_work):
        "test KeyboardInterrupt"
        fake_work.side_effect = KeyboardInterrupt()
        mock_flag = FakeFlag(0.01)
        test_object = TestObject()
        process.monitor_interrupt(lambda flag: test_object.work(mock_flag))
        self.assertTrue(mock_flag.green_value)
