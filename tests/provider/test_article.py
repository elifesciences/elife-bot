import unittest
from provider.article import article
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import mock, patch

class FakeBucket:
    def get_key(self, key):
        return key


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


bucket_files_mock_version = [ObjectView({'key': ObjectView({'name':'06498/elife-06498-fig1-v1.tif'})}),
                             ObjectView({'key': ObjectView({'name':'06498/elife-06498-resp-fig1-v3-80w.gif'})}),
                             ObjectView({'key': ObjectView({'name':'06498/elife-06498-v1.xml'})}),
                             ObjectView({'key': ObjectView({'name':'06498/elife-06498-v2.pdf'})}),
                             ObjectView({'key': ObjectView({'name':'06498/elife-06498-v2.xml'})}),
                             ObjectView({'key': ObjectView({'name':'06498/elife-06498-v3-download.xml'})})]

bucket_files_mock = [ObjectView({'key': ObjectView({'name':'06498/elife-06498-fig1-v1.tif'})}),
                     ObjectView({'key': ObjectView({'name':'06498/elife-06498-resp-fig1-v1-80w.gif'})}),
                     ObjectView({'key': ObjectView({'name':'06498/elife-06498-v1-download.xml'})}),
                     ObjectView({'key': ObjectView({'name':'06498/elife-06498-v1.xml'})}),
                     ObjectView({'key': ObjectView({'name':'06498/elife-06498-v1.pdf'})})]



class TestProviderArticle(unittest.TestCase):

    @patch('provider.simpleDB')
    def setUp(self, mock_simpleDB):
        mock_simpleDB.return_value = None
        self.articleprovider = article(settings_mock)

    @patch('provider.lax_provider.article_versions')
    def test_download_article_xml_from_s3_error_article_version_500(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 500, test_data.lax_article_versions_response_data
        result = self.articleprovider.download_article_xml_from_s3('08411')
        self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_download_article_xml_from_s3_error_article_version_404(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, test_data.lax_article_versions_response_data
        result = self.articleprovider.download_article_xml_from_s3('08411')
        self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_check_is_article_published_by_lax_200(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, test_data.lax_article_versions_response_data
        result = self.articleprovider.check_is_article_published_by_lax('10.7554/eLife.00013', True, True)
        self.assertEqual(result, True)

    @patch('provider.lax_provider.article_versions')
    def test_check_is_article_published_by_lax_200_empty_data(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, []
        result = self.articleprovider.check_is_article_published_by_lax('10.7554/eLife.00013', False, None)
        self.assertEqual(result, False)

    @patch('provider.lax_provider.article_versions')
    def test_check_is_article_published_by_lax_404(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, None
        result = self.articleprovider.check_is_article_published_by_lax('10.7554/eLife.00013', False, None)
        self.assertEqual(result, False)

    @patch.object(article, 'get_bucket_files')
    def test_get_xml_file_name_by_version(self, mock_get_bucket_files):
        fake_bucket = FakeBucket()
        mock_get_bucket_files.return_value = fake_bucket, bucket_files_mock_version
        result = self.articleprovider.get_xml_file_name(None, None, None, version="2")
        self.assertEqual(result, "elife-06498-v2.xml")

    @patch.object(article, 'get_bucket_files')
    def test_get_xml_file_name_no_version(self, mock_get_bucket_files):
        fake_bucket = FakeBucket()
        mock_get_bucket_files.return_value = fake_bucket, bucket_files_mock
        result = self.articleprovider.get_xml_file_name(None, None, None, version=None)
        self.assertEqual(result, "elife-06498-v1.xml")

    def test_tweet_url(self):
        tweet_url = self.articleprovider.get_tweet_url("10.7554/eLife.08411")
        self.assertEqual(
            tweet_url,
            "http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.08411+%40eLife")


if __name__ == '__main__':
    unittest.main()
