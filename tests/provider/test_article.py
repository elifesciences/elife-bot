import unittest
import provider.article as provider_module
from provider.article import article
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from mock import patch
from ddt import ddt, data, unpack


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


@ddt
class TestProviderArticle(unittest.TestCase):
    def setUp(self):
        self.articleprovider = article(settings_mock)

    @patch("provider.lax_provider.article_versions")
    def test_download_article_xml_from_s3_error_article_version_500(
        self, mock_article_versions
    ):
        mock_article_versions.return_value = (
            500,
            test_data.lax_article_versions_response_data,
        )
        result = self.articleprovider.download_article_xml_from_s3("08411")
        self.assertEqual(result, False)

    @patch("provider.lax_provider.article_versions")
    def test_download_article_xml_from_s3_error_article_version_404(
        self, mock_article_versions
    ):
        mock_article_versions.return_value = (
            404,
            test_data.lax_article_versions_response_data,
        )
        result = self.articleprovider.download_article_xml_from_s3("08411")
        self.assertEqual(result, False)

    @data(
        {
            "filename": "tests/test_data/elife00013.xml",
            "attrs": {
                "doi": "10.7554/eLife.00013",
                "doi_id": "00013",
                "doi_url": "https://doi.org/10.7554/eLife.00013",
                "lens_url": "https://lens.elifesciences.org/00013",
                "tweet_url": (
                    "http://twitter.com/intent/tweet?text="
                    + "https%3A%2F%2Fdoi.org%2F10.7554%2FeLife.00013+%40eLife"
                ),
                "pub_date_timestamp": 1350259200,
                "article_type": "research-article",
                "related_article_count": 1,
                "xlink_href": "10.7554/eLife.00242",
                "is_poa": False,
                "insight_doi": "10.7554/eLife.00242",
                "display_channel": ["Research article"],
                "authors_string": (
                    "Rosanna A Alegado, Laura W Brown, Shugeng Cao, Renee K Dermenjian, "
                    + "Richard Zuzow, Stephen R Fairclough, Jon Clardy, Nicole King"
                ),
            },
        },
        {
            "filename": "tests/test_data/elife_poa_e03977.xml",
            "attrs": {
                "doi": "10.7554/eLife.03977",
                "doi_id": "03977",
                "doi_url": "https://doi.org/10.7554/eLife.03977",
                "lens_url": "https://lens.elifesciences.org/03977",
                "tweet_url": (
                    "http://twitter.com/intent/tweet?text="
                    + "https%3A%2F%2Fdoi.org%2F10.7554%2FeLife.03977+%40eLife"
                ),
                "pub_date_timestamp": None,
                "article_type": "research-article",
                "related_article_count": 0,
                "xlink_href": None,
                "is_poa": True,
                "insight_doi": None,
                "display_channel": ["Research article"],
                "authors_string": (
                    "Xili Liu, Xin Wang, Xiaojing Yang, Sen Liu, Lingli Jiang, "
                    + "Yimiao Qu, Lufeng Hu, Qi Ouyang, Chao Tang"
                ),
            },
        },
        {
            "filename": "tests/test_data/elife04796.xml",
            "attrs": {
                "doi": "10.7554/eLife.04796",
                "doi_id": "04796",
                "doi_url": "https://doi.org/10.7554/eLife.04796",
                "lens_url": "https://lens.elifesciences.org/04796",
                "tweet_url": (
                    "http://twitter.com/intent/tweet?text="
                    + "https%3A%2F%2Fdoi.org%2F10.7554%2FeLife.04796+%40eLife"
                ),
                "pub_date_timestamp": 1437004800,
                "article_type": "research-article",
                "related_article_count": 0,
                "xlink_href": None,
                "is_poa": False,
                "insight_doi": None,
                "display_channel": ["Registered report"],
                "authors_string": (
                    "Steven Fiering, Lay-Hong Ang, Judith Lacoste, Tim D Smith, Erin Griner, "
                    + "Reproducibility Project: Cancer Biology"
                ),
            },
        },
        {
            "filename": "tests/test_data/elife09169.xml",
            "attrs": {
                "doi": "10.7554/eLife.09169",
                "doi_id": "09169",
                "doi_url": "https://doi.org/10.7554/eLife.09169",
                "lens_url": "https://lens.elifesciences.org/09169",
                "tweet_url": (
                    "http://twitter.com/intent/tweet?text="
                    + "https%3A%2F%2Fdoi.org%2F10.7554%2FeLife.09169+%40eLife"
                ),
                "pub_date_timestamp": 1433721600,
                "article_type": "correction",
                "related_article_count": 1,
                "xlink_href": "10.7554/eLife.06959",
                "is_poa": False,
                "insight_doi": None,
                "display_channel": ["Correction"],
                "authors_string": (
                    "Irawati Kandela, James Chou, Kartoa Chow, "
                    + "Reproducibility Project: Cancer Biology"
                ),
            },
        },
    )
    @unpack
    def test_parse_article_file(self, filename, attrs):
        parse_result = self.articleprovider.parse_article_file(filename)
        self.assertTrue(parse_result)
        self.assertEqual(self.articleprovider.doi, attrs.get("doi"))
        self.assertEqual(self.articleprovider.doi_id, attrs.get("doi_id"))
        self.assertEqual(self.articleprovider.doi_url, attrs.get("doi_url"))
        self.assertEqual(self.articleprovider.lens_url, attrs.get("lens_url"))
        self.assertEqual(self.articleprovider.tweet_url, attrs.get("tweet_url"))
        self.assertEqual(
            self.articleprovider.pub_date_timestamp, attrs.get("pub_date_timestamp")
        )
        self.assertEqual(self.articleprovider.article_type, attrs.get("article_type"))
        self.assertEqual(
            len(self.articleprovider.related_articles),
            attrs.get("related_article_count"),
        )
        if self.articleprovider.related_articles:
            self.assertEqual(
                self.articleprovider.related_articles[0].get("xlink_href"),
                attrs.get("xlink_href"),
            )
        self.assertEqual(self.articleprovider.is_poa, attrs.get("is_poa"))
        self.assertEqual(
            self.articleprovider.get_article_related_insight_doi(),
            attrs.get("insight_doi"),
        )
        self.assertEqual(
            self.articleprovider.display_channel, attrs.get("display_channel")
        )
        self.assertEqual(
            self.articleprovider.authors_string, attrs.get("authors_string")
        )

    def test_parse_article_file_failure(self):
        filename = None
        parse_result = self.articleprovider.parse_article_file(filename)
        self.assertFalse(parse_result)


class TestTweetUrl(unittest.TestCase):
    def test_tweet_url(self):
        tweet_url = provider_module.get_tweet_url("10.7554/eLife.08411")
        self.assertEqual(
            tweet_url,
            (
                "http://twitter.com/intent/tweet?text=https%3A%2F%2Fdoi.org"
                + "%2F10.7554%2FeLife.08411+%40eLife"
            ),
        )


class TestGetLensUrl(unittest.TestCase):
    def test_get_lens_url(self):
        lens_url = provider_module.get_lens_url("10.7554/eLife.08411")
        self.assertEqual(lens_url, "https://lens.elifesciences.org/08411")


@ddt
class TestIdFromPoaS3KeyName(unittest.TestCase):
    @data(
        {
            "s3_key_name": "published/20140508/elife_poa_e02419.xml",
            "expected_doi_id": 2419,
        },
        {
            "s3_key_name": "published/20140508/elife_poa_e02444v2.xml",
            "expected_doi_id": 2444,
        },
        {
            "s3_key_name": "pubmed/published/20140917/elife_poa_e03970.xml",
            "expected_doi_id": 3970,
        },
    )
    @unpack
    def test_get_doi_id_from_poa_s3_key_name(self, s3_key_name, expected_doi_id):
        doi_id = provider_module.get_doi_id_from_poa_s3_key_name(s3_key_name)
        self.assertEqual(doi_id, expected_doi_id)


@ddt
class TestIdFromS3KeyName(unittest.TestCase):
    @data(
        {
            "s3_key_name": "pubmed/published/20140923/elife02104.xml",
            "expected_doi_id": 2104,
        },
        {
            "s3_key_name": "pubmed/published/20141224/elife04034.xml",
            "expected_doi_id": 4034,
        },
    )
    @unpack
    def test_get_doi_id_from_s3_key_name(self, s3_key_name, expected_doi_id):
        doi_id = provider_module.get_doi_id_from_s3_key_name(s3_key_name)
        self.assertEqual(doi_id, expected_doi_id)
