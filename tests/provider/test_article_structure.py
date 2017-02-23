import unittest
from ddt import ddt, data, unpack
from provider.article_structure import ArticleInfo


@ddt
class TestArticleStructure(unittest.TestCase):

    @unpack
    @data({'input': 'elife-07702-vor-r4.zip', 'expected': None},
          {'input': 'elife-00013-vor-v1-20121015000000.zip', 'expected':'2012-10-15T00:00:00Z'})
    def test_get_update_date_from_zip_filename(self, input, expected):
        self.articleinfo = ArticleInfo(input)
        result = self.articleinfo.get_update_date_from_zip_filename()
        self.assertEqual(result, expected)

    @unpack
    @data({'input': 'elife-07702-vor-r4.zip', 'expected': None},
          {'input': 'elife-00013-vor-v1-20121015000000.zip', 'expected': '1'})
    def test_get_version_from_zip_filename(self, input, expected):
        self.articleinfo = ArticleInfo(input)
        result = self.articleinfo.get_version_from_zip_filename()
        self.assertEqual(result, expected)

    @unpack
    @data(
        {'input': 'elife-07702-vor-r4.zip', 'expected': 'ArticleZip'},
        {'input': 'elife-00013-vor-v1-20121015000000.zip', 'expected': 'ArticleZip'},
        {'input': 'elife-00666-v1.pdf', 'expected': 'Other'},
        {'input': 'elife-00666-v1.xml', 'expected': 'ArticleXML'},
        {'input': 'elife-00666-app1-fig1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-app1-fig1-figsupp1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-app2-video1.mp4', 'expected': 'Other'},
        {'input': 'elife-00666-box2-fig1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-code1-v1.xml', 'expected': 'Other'},
        {'input': 'elife-00666-data1-v1.xlsx', 'expected': 'Other'},
        {'input': 'elife-00666-fig1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig2-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig2-figsupp1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig2-figsupp2-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig3-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig3-figsupp1-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig3-video1.mp4', 'expected': 'Other'},
        {'input': 'elife-00666-fig4-v1.tif', 'expected': 'Figure'},
        {'input': 'elife-00666-fig4-code1-v1.xlsx', 'expected': 'Other'},
        {'input': 'elife-00666-figures-v1.pdf', 'expected': 'Other'},
        {'input': 'elife-00666-inf001-v1.jpeg', 'expected': 'Inline'},
        {'input': 'elife-00666-repstand1-v1.pdf', 'expected': 'Other'},
        {'input': 'elife-00666-resp-fig1-v1.png', 'expected': 'Figure'},
        {'input': 'elife-00666-resp-video1.mp4', 'expected': 'Other'},
        {'input': 'elife-00666-supp1-v1.csv', 'expected': 'Other'},
        {'input': 'elife-00666-table3-data1-v1.xlsx', 'expected': 'Other'},
        {'input': 'elife-00666-video1.mp4', 'expected': 'Other'},
        {'input': 'elife-00666-video1-data1-v1.xlsx', 'expected': 'Other'},
          )
    def test_get_file_type_from_zip_filename(self, input, expected):
        self.articleinfo = ArticleInfo(input)
        result = self.articleinfo.file_type
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
