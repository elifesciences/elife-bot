import unittest
from activity.activity_PubmedArticleDeposit import activity_PubmedArticleDeposit
import shutil
from mock import patch
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger
from provider.article import article
from provider.simpleDB import SimpleDB
from provider import lax_provider
import tests.test_data as test_case_data
import os
from ddt import ddt, data


@ddt
class TestPubmedArticleDeposit(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_PubmedArticleDeposit(settings_mock, fake_logger, None, None, None)


    def tearDown(self):
        self.activity.clean_tmp_dir()


    def input_dir(self):
        "return the staging dir name for the activity"
        return os.path.join(self.activity.get_tmp_dir(), self.activity.INPUT_DIR)


    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return os.path.join(self.activity.get_tmp_dir(), self.activity.TMP_DIR)


    def fake_download_files_from_s3_outbox(self, document):
        source_doc = "tests/test_data/pubmed/" + document
        dest_doc = self.input_dir() + os.sep + document
        shutil.copy(source_doc, dest_doc)


    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    @patch.object(activity_PubmedArticleDeposit, 'upload_pubmed_xml_to_s3')
    @patch.object(activity_PubmedArticleDeposit, 'clean_outbox')
    @patch.object(activity_PubmedArticleDeposit, 'ftp_files_to_endpoint')
    @patch.object(article, 'get_article_bucket_pub_date')
    @patch.object(lax_provider, 'was_ever_poa')
    @patch.object(lax_provider, 'published_considering_poa_status')
    @patch.object(lax_provider, 'article_highest_version')
    @patch.object(activity_PubmedArticleDeposit, 'get_outbox_s3_key_names')
    @patch.object(activity_PubmedArticleDeposit, 'download_files_from_s3_outbox')
    @data(
        {
            "comment": 'example PoA file will have an aheadofprint',
            "article_xml_filenames": ['elife-29353-v1.xml'],
            "ftp_files_return_value": True,
            "was_ever_poa": True,
            "published": True,
            "highest_version": 1,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_ftp_status": True,
            "expected_activity_status": True,
            "expected_file_count": 1,
            "expected_pubmed_xml_contains": [
                '<ArticleTitle>An evolutionary young defense metabolite influences the root growth of plants via the ancient TOR signaling pathway</ArticleTitle>',
                '<PubDate PubStatus="aheadofprint"><Year>2017</Year><Month>December</Month><Day>12</Day></PubDate>',
                '<ELocationID EIdType="doi">10.7554/eLife.29353</ELocationID>'
                ]
        },
        {
            "comment": 'example VoR file will have a Replaces tag',
            "article_xml_filenames": ['elife-15747-v2.xml'],
            "ftp_files_return_value": True,
            "was_ever_poa": False,
            "published": True,
            "highest_version": 2,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_ftp_status": True,
            "expected_activity_status": True,
            "expected_file_count": 1,
            "expected_pubmed_xml_contains": [
                '<Replaces IdType="doi">10.7554/eLife.15747</Replaces>',
                '<ArticleTitle>Community-level cohesion without cooperation</ArticleTitle>',
                '<PubDate PubStatus="epublish"><Year>2016</Year><Month>June</Month><Day>16</Day></PubDate>',
                '<ELocationID EIdType="doi">10.7554/eLife.15747</ELocationID>',
                '<Identifier Source="ORCID">http://orcid.org/0000-0002-9558-1121</Identifier>'
                ]
        },
        {
            "comment": 'test for if the article is published False (not published yet)',
            "article_xml_filenames": ['elife-15747-v2.xml'],
            "ftp_files_return_value": True,
            "was_ever_poa": False,
            "published": False,
            "highest_version": 1,
            "expected_result": True,
            "expected_approve_status": False,
            "expected_generate_status": False,
            "expected_publish_status": None,
            "expected_ftp_status": None,
            "expected_activity_status": True,
            "expected_file_count": 0
        },
        {
            "comment": 'test for if FTP status is False',
            "article_xml_filenames": ['elife-15747-v2.xml'],
            "ftp_files_return_value": False,
            "was_ever_poa": False,
            "published": True,
            "highest_version": 2,
            "expected_result": False,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": False,
            "expected_ftp_status": False,
            "expected_activity_status": False,
            "expected_file_count": 1,
        },
    )
    def test_do_activity(self, test_data, fake_download_files_from_s3_outbox, fake_get_outbox_s3_key_names,
                         fake_article_highest_version, fake_published_considering_poa_status, fake_was_ever_poa,
                         fake_get_article_bucket_pub_date, fake_ftp_files_to_endpoint,
                         fake_clean_outbox, fake_upload_pubmed_xml_to_s3,
                         fake_elife_add_email_to_email_queue):
        # copy XML files into the input directory
        for article_xml in test_data.get("article_xml_filenames"):
            fake_download_files_from_s3_outbox = self.fake_download_files_from_s3_outbox(article_xml)
        # set some return values for the mocks
        fake_get_outbox_s3_key_names.return_value = test_data.get("article_xml_filenames")
        fake_get_article_bucket_pub_date.return_value = None
        # lax data overrides
        fake_was_ever_poa.return_value = test_data.get("was_ever_poa")
        fake_published_considering_poa_status.return_value = test_data.get("published")
        fake_article_highest_version.return_value = test_data.get("highest_version")
        # ftp
        fake_ftp_files_to_endpoint.return_value = test_data.get("ftp_files_return_value")
        # do the activity
        result = self.activity.do_activity()
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.approve_status, test_data.get("expected_approve_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.generate_status, test_data.get("expected_generate_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.publish_status, test_data.get("expected_publish_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(self.activity.activity_status, test_data.get("expected_activity_status"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        # Count PubMed XML file in the tmp directory
        file_count = len(os.listdir(self.tmp_dir()))
        self.assertEqual(file_count, test_data.get("expected_file_count"),
                         'failed in {comment}'.format(comment=test_data.get("comment")))
        if file_count > 0 and test_data.get("expected_pubmed_xml_contains"):
            # Open the first Pubmed XML and check some of its contents
            pubmed_xml_filename_path = os.path.join(self.tmp_dir(), os.listdir(self.tmp_dir())[0])
            with open(pubmed_xml_filename_path, 'rb') as fp:
                pubmed_xml = fp.read()
                for expected in test_data.get("expected_pubmed_xml_contains"):
                    self.assertTrue(
                        expected in pubmed_xml,
                        'failed in {comment}: {expected} not found in pubmed_xml {path}'.format(
                            comment=test_data.get("comment"), expected=expected,
                            path=pubmed_xml_filename_path))

    @data(
        {
            "article_xml": 'elife-29353-v1.xml',
            "expected_article_count": 1,
            "expected_doi": '10.7554/eLife.29353'
        },
        {
            "article_xml": 'bad_xml.xml',
            "expected_article_count": 0
        }
    )
    def test_parse_article_xml(self, test_data):
        source_doc = "tests/test_data/pubmed/" + test_data.get('article_xml')
        articles = self.activity.parse_article_xml([source_doc])
        self.assertEqual(len(articles), test_data.get('expected_article_count'),
                         'failed comparing expected_article_count')
        if articles:
            article = articles[0]
            self.assertEqual(article.doi, test_data.get('expected_doi'),
                         'failed comparing expected_doi')
            # test the file name to DOI map
            self.assertEqual(self.activity.xml_file_to_doi_map.get(article.doi),
                             source_doc, 'failed checking the xml_file_to_doi_map')


if __name__ == '__main__':
    unittest.main()
