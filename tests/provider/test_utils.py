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

    @unpack
    @data(
        ('clean', 'clean'),
        ("  very \n   messy  ", 'very messy'),
        )
    def test_tidy_whitespace(self, string, expected):
        self.assertEqual(utils.tidy_whitespace(string), expected)

    @unpack
    @data(
        (None, 'VOR'),
        (True, 'POA'),
        (False, 'VOR'),
        ('Anything', 'POA'),
        )
    def test_article_status(self, value, expected):
        self.assertEqual(utils.article_status(value), expected)

    @unpack
    @data(
        (None, None),
        ("10.7554/eLife.00003", 3),
        ("not_a_doi", None)
        )
    def test_msid_from_doi(self, value, expected):
        self.assertEqual(utils.msid_from_doi(value), expected)

if __name__ == '__main__':
    unittest.main()
