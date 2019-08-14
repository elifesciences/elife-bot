import time
import unittest
from mock import patch
from testfixtures import TempDirectory
import provider.crossref as crossref
import tests.settings_mock as settings_mock
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeLogger, FakeResponse


def expected_http_detail(file_name, status_code):
    return [
        'XML file: ' + file_name,
        'HTTP status: ' + str(status_code),
        'HTTP response: '
    ]


class TestCrossrefProvider(unittest.TestCase):

    def setUp(self):
        self.directory = TempDirectory()
        self.good_xml_file = "tests/test_data/crossref/elife-18753-v1.xml"
        self.bad_xml_file = "tests/files_source/elife-00353-v1_bad_pub_date"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_elifecrossref_config(self):
        """test reading the crossref config file"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        self.assertIsNotNone(crossref_config)

    def test_parse_article_xml(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        self.assertEqual(len(articles), 1)

    def test_parse_article_xml_exception(self):
        articles = crossref.parse_article_xml([self.bad_xml_file], self.directory)
        self.assertEqual(len(articles), 0)

    @patch('provider.lax_provider.article_versions')
    def test_set_article_pub_date(self, mock_article_versions):
        """test for when the date is missing and uses lax data"""
        mock_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        # reset the dates
        article.dates = {}
        # now set the date
        crossref.set_article_pub_date(article, crossref_config, settings_mock, FakeLogger())
        self.assertEqual(len(article.dates), 1)

    def test_set_article_version(self):
        """test version when it is already present"""
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        # set the version but it is already set
        crossref.set_article_version(article, settings_mock)
        self.assertEqual(article.version, 1)

    @patch('provider.lax_provider.article_versions')
    def test_set_article_version_missing(self, mock_article_versions):
        """test setting version when missing"""
        mock_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        # reset the version
        article.version = None
        # now set the version
        crossref.set_article_version(article, settings_mock)
        self.assertEqual(article.version, 3)

    def test_article_first_pub_date(self):
        """test finding a pub date in the article dates"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        # get the pub date
        pub_date_object = crossref.article_first_pub_date(crossref_config, article)
        expected_date = time.strptime("2016-07-15 UTC", "%Y-%m-%d %Z")
        self.assertEqual(pub_date_object.date_type, "pub")
        self.assertEqual(pub_date_object.date, expected_date)

    def test_approve_to_generate(self):
        """test approving based on the pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    @patch('time.gmtime')
    def test_approve_to_generate_not_approved(self, mock_gmtime):
        """test approving if the pub date is after the mock current date"""
        mock_gmtime.return_value = (1, 1, 1, 1, 1, 1, 1, 1, 0)
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertFalse(approved)

    def test_approve_to_generate_no_date(self):
        """test approving when there is no pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory)
        article = articles[0]
        # reset the dates
        article.dates = {}
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    def test_crossref_data_payload(self):
        expected = {
            'operation': 'doMDUpload',
            'login_id': settings_mock.crossref_login_id,
            'login_passwd': settings_mock.crossref_login_passwd
        }
        payload = crossref.crossref_data_payload(
            settings_mock.crossref_login_id, settings_mock.crossref_login_passwd)
        self.assertEqual(payload, expected)

    @patch('requests.post')
    def test_upload_files_to_endpoint(self, fake_request):
        status_code = 200
        xml_files = [self.good_xml_file]

        fake_request.return_value = FakeResponse(status_code)

        expected_status = True
        expected_detail = expected_http_detail(self.good_xml_file, status_code)

        status, http_detail_list = crossref.upload_files_to_endpoint('', '', xml_files)
        self.assertEqual(status, expected_status)
        self.assertEqual(http_detail_list, expected_detail)

    @patch('requests.post')
    def test_upload_files_to_endpoint_failure(self, fake_request):
        status_code = 500
        xml_files = [self.good_xml_file]

        fake_request.return_value = FakeResponse(status_code)

        expected_status = False
        expected_detail = expected_http_detail(self.good_xml_file, status_code)

        status, http_detail_list = crossref.upload_files_to_endpoint('', '', xml_files)
        self.assertEqual(status, expected_status)
        self.assertEqual(http_detail_list, expected_detail)
