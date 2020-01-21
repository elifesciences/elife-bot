import os
import shutil
import time
import unittest
from collections import OrderedDict
from mock import patch
from testfixtures import TempDirectory
from elifearticle.article import ArticleDate
import provider.crossref as crossref
import tests.settings_mock as settings_mock
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
import tests.activity.helpers as helpers
import tests.activity.test_activity_data as activity_test_data


def expected_http_detail(file_name, status_code):
    return [
        'XML file: ' + file_name,
        'HTTP status: ' + str(status_code),
        'HTTP response: '
    ]


class TestCrossrefProvider(unittest.TestCase):

    def setUp(self):
        self.directory = TempDirectory()
        self.good_xml_file = "tests/test_data/crossref/outbox/elife-18753-v1.xml"
        self.bad_xml_file = "tests/test_data/activity.json"

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=['.gitkeep'])

    def test_elifecrossref_config(self):
        """test reading the crossref config file"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        self.assertIsNotNone(crossref_config)

    def test_parse_article_xml(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        self.assertEqual(len(articles), 1)

    def test_parse_article_xml_exception(self):
        articles = crossref.parse_article_xml([self.bad_xml_file], self.directory.path)
        self.assertEqual(len(articles), 0)

    def test_article_xml_list_parse(self):
        article_xml_files = [self.good_xml_file, self.bad_xml_file]
        bad_xml_files = []
        article_object_map = crossref.article_xml_list_parse(
            article_xml_files, bad_xml_files, self.directory.path)
        # one good article in the map, one bad xml file in the bad_xml_files list
        self.assertEqual(len(article_object_map), 1)
        self.assertEqual(len(bad_xml_files), 1)

    @patch('provider.lax_provider.article_versions')
    def test_set_article_pub_date(self, mock_article_versions):
        """test for when the date is missing and uses lax data"""
        mock_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # reset the dates
        article.dates = {}
        # now set the date
        crossref.set_article_pub_date(article, crossref_config, settings_mock, FakeLogger())
        self.assertEqual(len(article.dates), 1)

    def test_set_article_version(self):
        """test version when it is already present"""
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # set the version but it is already set
        crossref.set_article_version(article, settings_mock)
        self.assertEqual(article.version, 1)

    @patch('provider.lax_provider.article_versions')
    def test_set_article_version_missing(self, mock_article_versions):
        """test setting version when missing"""
        mock_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
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
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
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
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    @patch('time.gmtime')
    def test_approve_to_generate_not_approved(self, mock_gmtime):
        """test approving if the pub date is after the mock current date"""
        mock_gmtime.return_value = (1, 1, 1, 1, 1, 1, 1, 1, 0)
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertFalse(approved)

    def test_approve_to_generate_no_date(self):
        """test approving when there is no pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # reset the dates
        article.dates = {}
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    def test_approve_to_generate_list(self):
        """test approving a list of files based on the pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        article = crossref.parse_article_xml([self.good_xml_file], self.directory.path)[0]
        # make a fake article with a future pub date
        future_article = crossref.parse_article_xml([self.good_xml_file], self.directory.path)[0]
        future_date = ArticleDate('pub', time.strptime("2999-07-15 UTC", "%Y-%m-%d %Z"))
        future_article.dates = {}
        future_article.add_date(future_date)
        # assemble the map of article objects
        article_object_map = OrderedDict([
            (self.good_xml_file, article),
            ('future_article.xml', future_article)
        ])
        bad_xml_files = []
        approved = crossref.approve_to_generate_list(
            article_object_map, crossref_config, bad_xml_files)
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(bad_xml_files), 1)

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

    def test_generate_crossref_xml_to_disk(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article_object_map = OrderedDict([
            (self.good_xml_file, articles[0]),
            ('fake_file_will_raise_exception.xml', None)
        ])
        good_xml_files = []
        bad_xml_files = []
        crossref_config = crossref.elifecrossref_config(settings_mock)
        result = crossref.generate_crossref_xml_to_disk(
            article_object_map, crossref_config, good_xml_files, bad_xml_files)
        self.assertTrue(result)
        self.assertEqual(len(good_xml_files), 1)
        self.assertEqual(len(bad_xml_files), 1)

    def test_get_to_folder_name(self):
        folder_name = ''
        date_stamp = ''
        expected = folder_name + date_stamp + '/'
        self.assertEqual(crossref.get_to_folder_name(folder_name, date_stamp), expected)

    @patch('provider.crossref.storage_context')
    def test_get_outbox_s3_key_names(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext('tests/test_data/crossref/outbox/')
        outbox_folder = 'crossref/outbox/'
        expected = [outbox_folder.rstrip('/') + '/' + 'elife-00353-v1.xml']
        key_names = crossref.get_outbox_s3_key_names(settings_mock, '', outbox_folder)
        # returns the default file name from FakeStorageContext in the test scenario
        self.assertEqual(key_names, expected)

    @patch('provider.crossref.storage_context')
    def test_download_files_from_s3_outbox(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        bucket_name = ''
        outbox_folder = ''
        key_names = crossref.get_outbox_s3_key_names(settings_mock, bucket_name, outbox_folder)
        result = crossref.download_files_from_s3_outbox(
            settings_mock, bucket_name, key_names, self.directory.path, FakeLogger())
        self.assertTrue(result)

    @patch.object(FakeStorageContext, 'get_resource_to_file')
    @patch('provider.crossref.storage_context')
    def test_download_files_from_s3_outbox_failure(self, fake_storage_context, fake_get_resource):
        """test IOError exception for coverage"""
        fake_storage_context.return_value = FakeStorageContext()
        fake_get_resource.side_effect = IOError
        bucket_name = ''
        outbox_folder = ''
        key_names = crossref.get_outbox_s3_key_names(settings_mock, bucket_name, outbox_folder)
        result = crossref.download_files_from_s3_outbox(
            settings_mock, bucket_name, key_names, self.directory.path, FakeLogger())
        self.assertFalse(result)

    @patch('provider.crossref.storage_context')
    def test_clean_outbox(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext(self.directory)
        # copy two files in for cleaning
        shutil.copy(self.good_xml_file, self.directory.path)
        shutil.copy(self.bad_xml_file, self.directory.path)
        # add outbox_folder name and one file to the list of published file names
        bucket_name = 'bucket'
        outbox_folder = 'crossref/outbox/'
        to_folder = 'crossref/published/'
        published_file_names = [outbox_folder, self.good_xml_file]
        # clean outbox
        crossref.clean_outbox(
            settings_mock, bucket_name, outbox_folder, to_folder, published_file_names)
        # TempDirectory should have one file remaining
        self.assertTrue(len(os.listdir(self.directory.path)), 1)

    @patch('provider.crossref.storage_context')
    def test_upload_crossref_xml_to_s3(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        file_names = [self.good_xml_file]
        expected = [file_name.split(os.sep)[-1] for file_name in file_names]
        crossref.upload_crossref_xml_to_s3(settings_mock, 'bucket', 'to_folder/', file_names)
        # filter out the .gitkeep file before comparing
        uploaded_files = [
            file_name for file_name in
            os.listdir(activity_test_data.ExpandArticle_files_dest_folder)
            if file_name.endswith('.xml')]
        self.assertEqual(uploaded_files, expected)


class TestDoiExists(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.doi = '10.7554/eLife.99999'

    @patch('requests.head')
    def test_doi_exists_302(self, fake_request):
        fake_request.return_value = FakeResponse(302)
        self.assertTrue(crossref.doi_exists(self.doi, self.logger))

    @patch('requests.head')
    def test_doi_exists_404(self, fake_request):
        fake_request.return_value = FakeResponse(404)
        self.assertFalse(crossref.doi_exists(self.doi, self.logger))

    @patch('requests.head')
    def test_doi_exists_200(self, fake_request):
        fake_request.return_value = FakeResponse(200)
        self.assertFalse(crossref.doi_exists(self.doi, self.logger))
        self.assertTrue(
            self.logger.loginfo.endswith('Status code for 10.7554/eLife.99999 was 200'))
