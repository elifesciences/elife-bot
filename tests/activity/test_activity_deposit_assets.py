import unittest
from activity.activity_DepositAssets import activity_DepositAssets
import settings_mock
from ddt import ddt, data, unpack


@ddt
class TestDepositAssets(unittest.TestCase):
    def setUp(self):
        self.depositassets = activity_DepositAssets(settings_mock, None, None, None, None)

    @unpack
    @data({'input': '.tif', 'expected': ['.tif']},
          {'input': '.jpg, .tiff, .png', 'expected':['.jpg', '.tiff', '.png']})
    def test_get_no_download_extensions(self, input, expected):
        result = self.depositassets.get_no_download_extensions(input)
        self.assertListEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
