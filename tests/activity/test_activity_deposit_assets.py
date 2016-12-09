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

    @unpack
    @data(
        (None, None),
        ('image.jpg', 'image/jpeg'),
        ('/folder/file.test.pdf', 'application/pdf'),
        ('/folder/weird_file.wdl', 'binary/octet-stream'),
        ('a_file', 'binary/octet-stream')
        )
    def test_content_type_from_file_name(self, input, expected):
        result = self.depositassets.content_type_from_file_name(input)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
