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

if __name__ == '__main__':
    unittest.main()
