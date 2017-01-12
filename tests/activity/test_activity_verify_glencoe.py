import unittest
from activity.activity_VerifyGlencoe import activity_VerifyGlencoe
import settings_mock

class TestVerifyGlencoe(unittest.TestCase):

    def setUp(self):
        self.verifyglencoe = activity_VerifyGlencoe(settings_mock, None, None, None, None)

    def test_check_msid_long_id(self):
        result = self.verifyglencoe.check_msid("7777777701234")
        self.assertEqual('01234', result)

    def test_check_msdi_proper_id(self):
        result = self.verifyglencoe.check_msid("01234")
        self.assertEqual('01234', result)

    def test_check_msdi_short_id(self):
        result = self.verifyglencoe.check_msid("34")
        self.assertEqual('00034', result)



if __name__ == '__main__':
    unittest.main()
