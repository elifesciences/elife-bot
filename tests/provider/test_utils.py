import unittest
from ddt import ddt, data, unpack
import provider.utils as utils


@ddt
class TestUtils(unittest.TestCase):

    def setUp(self):
        pass

    @unpack
    @data(
        (7, '00007'),
        ('7', '00007'),
        )
    def test_pad_msid(self, msid, expected):
        self.assertEqual(utils.pad_msid(msid), expected)

    @unpack
    @data(
        (2, '02'),
        ('2', '02'),
        )
    def test_pad_volume(self, volume, expected):
        self.assertEqual(utils.pad_volume(volume), expected)



if __name__ == '__main__':
    unittest.main()
