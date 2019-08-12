import unittest
from activity.activity_DepositCrossref import activity_DepositCrossref
import shutil
from mock import patch
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
from provider.article import article
from provider.simpleDB import SimpleDB
from provider import lax_provider
import tests.test_data as test_case_data
import os
from ddt import ddt, data


@ddt
class TestDepositCrossref(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossref(settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def input_dir(self):
        "return the staging dir name for the activity"
        return self.activity.directories.get("INPUT_DIR")

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    def fake_download_files_from_s3_outbox(self, document):
        source_doc = "tests/test_data/crossref/" + document
        dest_doc = self.input_dir() + os.sep + document
        shutil.copy(source_doc, dest_doc)

    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    @patch.object(activity_DepositCrossref, 'upload_crossref_xml_to_s3')
    @patch.object(activity_DepositCrossref, 'clean_outbox')
    @patch.object(activity_DepositCrossref, 'deposit_files_to_endpoint')
    @patch.object(activity_DepositCrossref, 'get_outbox_s3_key_names')
    @patch.object(activity_DepositCrossref, 'download_files_from_s3_outbox')
    @data(
        {
            "article_xml_filenames": ['elife-15747-v2.xml'],
            "deposit_files_return_value": True,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_activity_status": True,
            "expected_file_count": 1,
            "expected_crossref_xml_contains": [
                '<doi>10.7554/eLife.15747</doi>',
                '<publication_date media_type="online"><month>06</month><day>16</day><year>2016</year></publication_date>',
                '<item_number item_number_type="article_number">e15747</item_number>',
                '<citation key="bib13"><journal_title>BMC Biology</journal_title><author>Gilbert</author><volume>12</volume><cYear>2014</cYear><article_title>The Earth Microbiome project: successes and aspirations</article_title><doi>10.1186/s12915-014-0069-1</doi><elocation_id>69</elocation_id></citation>'
                ]
        },
        {
            "article_xml_filenames": ['elife-18753-v1.xml', 'elife-23065-v1.xml', 'fake-00000-v1.xml'],
            "deposit_files_return_value": True,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_activity_status": True,
            "expected_file_count": 2,
        },
        {
            "article_xml_filenames": [],
            "deposit_files_return_value": True,
            "expected_result": True,
            "expected_approve_status": False,
            "expected_generate_status": True,
            "expected_publish_status": None,
            "expected_activity_status": True,
            "expected_file_count": 0,
        },
        {
            "article_xml_filenames": ['elife-18753-v1.xml'],
            "deposit_files_return_value": False,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": False,
            "expected_activity_status": False,
            "expected_file_count": 1,
        },
    )
    def test_do_activity(self, test_data, fake_download_files_from_s3_outbox, fake_get_outbox_s3_key_names,
                         fake_deposit_files_to_endpoint,
                         fake_clean_outbox, fake_upload_crossref_xml_to_s3,
                         fake_elife_add_email_to_email_queue):
        # copy XML files into the input directory
        for article_xml in test_data.get("article_xml_filenames"):
            fake_download_files_from_s3_outbox = self.fake_download_files_from_s3_outbox(article_xml)
        # set some return values for the mocks
        fake_get_outbox_s3_key_names.return_value = test_data.get("article_xml_filenames")
        fake_deposit_files_to_endpoint.return_value = test_data.get("deposit_files_return_value")
        # do the activity
        result = self.activity.do_activity()
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        self.assertEqual(self.activity.approve_status, test_data.get("expected_approve_status"))
        self.assertEqual(self.activity.generate_status, test_data.get("expected_generate_status"))
        self.assertEqual(self.activity.publish_status, test_data.get("expected_publish_status"))
        self.assertEqual(self.activity.activity_status, test_data.get("expected_activity_status"))
        # Count crossref XML file in the tmp directory
        file_count = len(os.listdir(self.tmp_dir()))
        self.assertEqual(file_count, test_data.get("expected_file_count"))
        if file_count > 0 and test_data.get("expected_crossref_xml_contains"):
            # Open the first crossref XML and check some of its contents
            crossref_xml_filename_path = os.path.join(self.tmp_dir(), os.listdir(self.tmp_dir())[0])
            with open(crossref_xml_filename_path, 'rb') as fp:
                crossref_xml = fp.read().decode('utf8')
                for expected in test_data.get("expected_crossref_xml_contains"):
                    self.assertTrue(
                        expected in crossref_xml, '{expected} not found in crossref_xml {path}'.format(
                            expected=expected, path=crossref_xml_filename_path))

    @patch('provider.lax_provider.article_versions')
    def test_parse_article_xml(self, mock_lax_provider_article_versions):
        "example where there is not pub date and no version for an article"
        mock_lax_provider_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        articles = self.activity.parse_article_xml(['tests/test_data/crossref/elife_poa_e03977.xml'])
        article = articles[0]
        self.assertIsNotNone(article.get_date('pub'), 'date of type pub not found in article get_date()')
        self.assertIsNotNone(article.version, 'version is None in article')


    @patch('activity.activity_DepositCrossref.storage_context')
    def test_get_outbox_s3_key_names(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext('tests/test_data/crossref')
        key_names = self.activity.get_outbox_s3_key_names()
        # returns the default file name from FakeStorageContext in the test scenario
        self.assertEqual(key_names, ['elife-00353-v1.xml'])


if __name__ == '__main__':
    unittest.main()
