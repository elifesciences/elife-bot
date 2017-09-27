import unittest
from activity.activity_DepositCrossref import activity_DepositCrossref
import shutil
from mock import patch
import tests.activity.settings_mock as settings_mock
from provider.article import article
from provider.simpleDB import SimpleDB
import os


class TestDepositCrossref(unittest.TestCase):

    def setUp(self):
        self.activity = activity_DepositCrossref(settings_mock, None, None, None, None)


    def tearDown(self):
        self.activity.clean_tmp_dir()


    def input_dir(self):
        "return the staging dir name for the activity"
        return os.path.join(self.activity.get_tmp_dir(), self.activity.INPUT_DIR)


    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return os.path.join(self.activity.get_tmp_dir(), self.activity.TMP_DIR)


    def fake_download_files_from_s3_outbox(self, document):
        source_doc = "tests/test_data/crossref/" + document
        dest_doc = self.input_dir() + os.sep + document
        shutil.copy(source_doc, dest_doc)


    @patch.object(SimpleDB, 'elife_add_email_to_email_queue')
    @patch.object(activity_DepositCrossref, 'upload_crossref_xml_to_s3')
    @patch.object(activity_DepositCrossref, 'clean_outbox')
    @patch.object(activity_DepositCrossref, 'deposit_files_to_endpoint')
    @patch.object(article, 'get_article_bucket_pub_date')
    @patch.object(activity_DepositCrossref, 'get_outbox_s3_key_names')
    @patch.object(activity_DepositCrossref, 'download_files_from_s3_outbox')
    def test_do_activity(self, fake_download_files_from_s3_outbox, fake_get_outbox_s3_key_names,
                         fake_get_article_bucket_pub_date, fake_deposit_files_to_endpoint,
                         fake_clean_outbox, fake_upload_crossref_xml_to_s3,
                         fake_elife_add_email_to_email_queue):
        article_xml_filename = 'elife-15747-v2.xml'
        expected_crossref_xml_contains = [
            '<doi>10.7554/eLife.15747</doi>',
            '<publication_date media_type="online"><month>06</month><day>16</day><year>2016</year></publication_date>'
        ]
        fake_download_files_from_s3_outbox = self.fake_download_files_from_s3_outbox(article_xml_filename)
        fake_get_outbox_s3_key_names.return_value = [article_xml_filename]
        fake_get_article_bucket_pub_date.return_value = None
        fake_deposit_files_to_endpoint.return_value = True
        # do the activity
        result = self.activity.do_activity()
        self.assertTrue(result)
        self.assertTrue(self.activity.approve_status)
        self.assertTrue(self.activity.generate_status)
        # Will have one crossref XML file in the tmp directory
        self.assertEqual(len(os.listdir(self.tmp_dir())), 1)
        crossref_xml_filename_path = os.path.join(self.tmp_dir(), os.listdir(self.tmp_dir())[0])
        # Open the crossref XML and check some of its contents
        with open(crossref_xml_filename_path, 'rb') as fp:
            crossref_xml = fp.read()
            for expected in expected_crossref_xml_contains:
                try:
                    self.assertTrue(expected in crossref_xml)
                except AssertionError:
                    print expected, ' not found in crossref_xml'
                    raise


if __name__ == '__main__':
    unittest.main()
