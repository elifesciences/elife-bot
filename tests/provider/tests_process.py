import unittest

from provider.process import Flag

class TestExpandArticle(unittest.TestCase):
    def test_flag_starts_green_and_become_red_upon_termination_signal(self):
        flag = Flag()
        self.assertTrue(flag.green())
        self.assertFalse(flag.red())
        flag.stop_process()
        self.assertFalse(flag.green())
        self.assertTrue(flag.red())
