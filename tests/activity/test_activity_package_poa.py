import unittest
import os
import json
import shutil
import glob
from xml.parsers.expat import ExpatError
from mock import patch
from ddt import ddt, data, unpack
from packagepoa import transform
import provider.lax_provider as lax_provider
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data
import tests.activity.helpers as helpers
from tests.classes_mock import FakeSMTPServer
import activity.activity_PackagePOA as activity_module
from activity.activity_PackagePOA import activity_PackagePOA
from activity.activity_PackagePOA import get_doi_from_zip_file, approve_for_packaging


def outbox_files(folder):
    "count the files in the folder ignoring .gitkeep or files starting with ."
    return [file_name for file_name in os.listdir(folder) if not file_name.startswith('.')]


@ddt
class TestPackagePOA(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.poa = activity_PackagePOA(settings_mock, self.logger, None, None, None)
        self.test_data_dir = "tests/test_data/poa"

    def tearDown(self):
        self.poa.clean_tmp_dir()
        helpers.delete_files_in_folder(activity_test_data.ExpandArticle_files_dest_folder,
                                       filter_out=['.gitkeep'])

    def fake_download_latest_csv(self):
        csv_files = glob.glob(self.test_data_dir + "/*.csv")
        for file_name_path in csv_files:
            file_name = file_name_path.split(os.sep)[-1]
            shutil.copy(file_name_path, os.path.join(self.poa.directories.get("CSV"), file_name))

    def fake_download_poa_zip(self, document):
        if document:
            source_doc = self.test_data_dir + "/" + document
            dest_doc = os.path.join(self.poa.directories.get("EJP_INPUT"), document)
            try:
                shutil.copy(source_doc, dest_doc)
            except IOError:
                pass
            return dest_doc
        return None

    def fake_copy_pdf_to_hw_staging_dir(self, decap_pdf):
        if decap_pdf:
            source_doc = self.test_data_dir + "/" + decap_pdf
            dest_doc = os.path.join(self.poa.directories.get("DECAPITATE_PDF"), decap_pdf)
            try:
                shutil.copy(source_doc, dest_doc)
            except IOError:
                pass

    def check_ds_zip_exists(self, ds_zip):
        """
        After do_activity, check the directory contains a zip with ds_zip file name
        """
        file_names = glob.glob(self.poa.directories.get("OUTPUT") + os.sep + "*")
        for file_name_path in file_names:
            if file_name_path.split(os.sep)[-1] == ds_zip:
                return True
        return False

    @unpack
    @data(
        (None, None),
        ('tests/test_data/poa/18022_1_supp_mat_highwire_zip_268991_x75s4v.zip',
         '10.7554/eLife.12717'),
        # test not a zip file
        ('tests/test_data/poa/poa_abstract.csv',
         None),
        )
    def test_get_doi_from_zip_file(self, filename, expected):
        "test getting doi from the zip file manifest"
        self.assertEqual(get_doi_from_zip_file(filename), expected)

    @unpack
    @data(
        (None, False),
        ('10.7554/eLife.12717', True),
        )
    def test_approve_for_packaging(self, doi_id, expected):
        "test approving to package or not"
        self.assertEqual(approve_for_packaging(doi_id), expected)

    @patch.object(transform, 'copy_pdf_to_output_dir')
    @data(
        {
            'filename': '18022_1_supp_mat_highwire_zip_268991_x75s4v.zip',
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            'expected': True
        },
        {
            'filename': None,
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            'expected': False
        },
        {
            # test not a zip file
            'filename': 'poa_abstract.csv',
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            'expected': False
        }
        )
    def test_process_poa_zipfile(self, test_data, fake_copy_pdf_to_output_dir):
        "test processing the zip file directly"
        self.poa.make_activity_directories()
        fake_copy_pdf_to_output_dir.return_value = None
        self.fake_copy_pdf_to_hw_staging_dir(test_data.get('poa_decap_pdf'))
        file_path = self.fake_download_poa_zip(test_data.get('filename'))
        print(file_path)
        self.assertEqual(self.poa.process_poa_zipfile(file_path), test_data.get('expected'))

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('activity.activity_PackagePOA.storage_context')
    @patch("provider.ejp.EJP.latest_s3_file_name_by_convention")
    @patch('provider.ejp.EJP.ejp_bucket_file_list')
    @patch.object(lax_provider, 'article_publication_date')
    @patch.object(activity_PackagePOA, 'clean_tmp_dir')
    @patch.object(transform, 'copy_pdf_to_output_dir')
    @data(
        {
            "scenario": "1",
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            "doi": "10.7554/eLife.12717",
            "ds_zip": "elife_poa_e12717_ds.zip",
            "pub_date": "20160514000000",
            "expected_generate_xml_status": True,
            "expected_process_status": True,
            "expected_approve_status": True,
            "expected_pdf_decap_status": True,
            "expected_activity_status": True,
            "expected_ds_zip_exists": True,
            "expected_result": True,
            "expected_outbox_count": 3
        },
        {
            "scenario": "2",
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            "doi": "10.7554/eLife.12717",
            "ds_zip": "elife_poa_e12717_ds.zip",
            "pub_date": None,
            "expected_generate_xml_status": True,
            "expected_process_status": True,
            "expected_approve_status": True,
            "expected_pdf_decap_status": True,
            "expected_activity_status": True,
            "expected_ds_zip_exists": True,
            "expected_result": True,
            "expected_outbox_count": 3
        },
        {
            # test bad input file
            "scenario": "3",
            "poa_input_zip": None,
            "poa_decap_pdf": None,
            "doi": None,
            "ds_zip": None,
            "pub_date": None,
            "expected_generate_xml_status": None,
            "expected_process_status": None,
            "expected_approve_status": False,
            "expected_pdf_decap_status": None,
            "expected_activity_status": False,
            "expected_ds_zip_exists": False,
            "expected_result": True,
            "expected_outbox_count": 0
        },
        {
            # test pdf decap failure
            "scenario": "4",
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": None,
            "doi": "10.7554/eLife.12717",
            "ds_zip": "elife_poa_e12717_ds.zip",
            "pub_date": None,
            "expected_generate_xml_status": True,
            "expected_process_status": True,
            "expected_approve_status": True,
            "expected_pdf_decap_status": False,
            "expected_activity_status": False,
            "expected_ds_zip_exists": True,
            "expected_result": True,
            "expected_outbox_count": 2
        },
    )
    def test_do_activity(self, test_data, fake_copy_pdf_to_output_dir, fake_clean_tmp_dir,
                         fake_article_publication_date, fake_ejp_bucket_file_list,
                         fake_by_convention, fake_storage_context, fake_email_smtp_connect):
        # make directories first
        self.poa.make_activity_directories()
        # mock things
        fake_copy_pdf_to_output_dir.return_value = None
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.poa.get_tmp_dir())
        test_outbox_folder = activity_test_data.ExpandArticle_files_dest_folder
        bucket_list_file = os.path.join("tests", "test_data", "ejp_bucket_list_new.json")
        with open(bucket_list_file, 'rb') as open_file:
            fake_ejp_bucket_file_list.return_value = json.loads(open_file.read().decode())
        fake_by_convention.return_value = None
        fake_storage_context.return_value = FakeStorageContext(directory=self.test_data_dir)
        if "pub_date" in test_data and test_data["pub_date"]:
            fake_article_publication_date.return_value = test_data["pub_date"]
        else:
            fake_article_publication_date.return_value = None

        # For now mock the PDF decapitator during tests
        self.fake_copy_pdf_to_hw_staging_dir(test_data.get('poa_decap_pdf'))

        param_data = json.loads('{"data": {"document": "' +
                                str(test_data["poa_input_zip"]) + '"}}')
        success = self.poa.do_activity(param_data)

        self.assertEqual(test_data["doi"], self.poa.doi)
        self.boolean_assertion(self.poa.generate_xml_status,
                               test_data.get('expected_generate_xml_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.poa.process_status,
                               test_data.get('expected_process_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.poa.approve_status,
                               test_data.get('expected_approve_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.poa.pdf_decap_status,
                               test_data.get('expected_pdf_decap_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.poa.activity_status,
                               test_data.get('expected_activity_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.check_ds_zip_exists(test_data["ds_zip"]),
                               test_data.get('expected_ds_zip_exists'),
                               test_data.get('scenario'))
        self.boolean_assertion(success,
                               test_data.get('expected_result'),
                               test_data.get('scenario'))
        # count the outbox files except the hidden .gitkeep file
        if test_data.get('expected_outbox_count'):
            self.boolean_assertion(len(outbox_files(test_outbox_folder)),
                                   test_data.get('expected_outbox_count'),
                                   test_data.get('scenario'))
        # check logging of CSV file S3 object last_modified date
        if test_data.get('expected_activity_status'):
            loginfo_message = (
                'CSV file '
                's3://ejp_bucket/ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv'
                ' last_modified: 2021-01-01T00:00:01.000Z')
            self.assertTrue(
                loginfo_message in self.logger.loginfo,
                'failed in scenario %s' % test_data.get('scenario'))

    def boolean_assertion(self, value, expected, scenario=None):
        "shorthand for checking and displaying output for equality assertions"
        self.assertEqual(value, expected,
                         "{value} does not equal {expected}, scenario {scenario}".format(
                             value=value,
                             expected=expected,
                             scenario=scenario))

    @patch.object(activity_PackagePOA, 'generate_xml')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('activity.activity_PackagePOA.storage_context')
    @patch("provider.ejp.EJP.latest_s3_file_name_by_convention")
    @patch('provider.ejp.EJP.ejp_bucket_file_list')
    @patch.object(lax_provider, 'article_publication_date')
    @patch.object(activity_PackagePOA, 'clean_tmp_dir')
    @patch.object(transform, 'copy_pdf_to_output_dir')
    @data(
        {
            "scenario": "1",
            "poa_input_zip": "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip",
            "poa_decap_pdf": "decap_elife_poa_e12717.pdf",
            "doi": "10.7554/eLife.12717",
            "expected_generate_xml_status": False,
            "expected_activity_status": False,
            "expected_result": True,
            "expected_outbox_count": 2
        },
    )
    def test_do_activity_generate_xml_exception(
            self, test_data, fake_copy_pdf_to_output_dir, fake_clean_tmp_dir,
            fake_article_publication_date, fake_ejp_bucket_file_list, fake_by_convention,
            fake_storage_context, fake_email_smtp_connect, fake_generate_xml):
        # make directories first
        self.poa.make_activity_directories()
        # mock things
        fake_generate_xml.side_effect = ExpatError('An exception')
        fake_copy_pdf_to_output_dir.return_value = None
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.poa.get_tmp_dir())
        test_outbox_folder = activity_test_data.ExpandArticle_files_dest_folder
        bucket_list_file = os.path.join("tests", "test_data", "ejp_bucket_list_new.json")
        fake_by_convention.return_value = None
        with open(bucket_list_file, 'rb') as open_file:
            fake_ejp_bucket_file_list.return_value = json.loads(open_file.read().decode())
        fake_storage_context.return_value = FakeStorageContext(directory=self.test_data_dir)
        fake_article_publication_date.return_value = None

        # For now mock the PDF decapitator during tests
        self.fake_copy_pdf_to_hw_staging_dir(test_data.get('poa_decap_pdf'))

        param_data = json.loads('{"data": {"document": "' +
                                str(test_data["poa_input_zip"]) + '"}}')
        success = self.poa.do_activity(param_data)

        self.assertEqual(test_data["doi"], self.poa.doi)
        self.boolean_assertion(self.poa.generate_xml_status,
                               test_data.get('expected_generate_xml_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(self.poa.activity_status,
                               test_data.get('expected_activity_status'),
                               test_data.get('scenario'))
        self.boolean_assertion(success,
                               test_data.get('expected_result'),
                               test_data.get('scenario'))
        # count the outbox files except the hidden .gitkeep file
        if test_data.get('expected_outbox_count'):
            self.boolean_assertion(len(outbox_files(test_outbox_folder)),
                                   test_data.get('expected_outbox_count'),
                                   test_data.get('scenario'))

    @patch.object(activity_module.parse, "build_article")
    def test_generate_xml_build_article_exception(self, fake_build_article):
        fake_build_article.side_effect = Exception("An exception")
        with self.assertRaises(Exception):
            self.poa.generate_xml(12717)
        self.assertEqual(
            self.poa.logger.logexception,
            "Exception in build_article for article_id 12717: An exception",
        )

    @patch.object(activity_module.parse, "build_article")
    def test_generate_xml_build_article_errors(self, fake_build_article):
        article_id = 12717
        error_count = 1
        error_messages = ["article_id %s error in set_title" % article_id]
        fake_build_article.return_value = None, error_count, error_messages
        with self.assertRaises(Exception):
            self.poa.generate_xml(article_id)
        self.assertEqual(
            self.poa.logger.logexception,
            (
                "Exception raised in generate_xml, error count: %s, error_messages: %s"
                % (error_count, ", ".join(error_messages))
            ),
        )

    @patch.object(activity_module.generate, 'build_xml_to_disk')
    def test_generate_xml_expat_exception(self, fake_build_xml):
        fake_build_xml.side_effect = ExpatError('An exception')
        with self.assertRaises(ExpatError):
            self.poa.generate_xml(12717)
        self.assertEqual(
            self.poa.logger.logexception,
            'Exception in build_xml_to_disk for article_id 12717: An exception')

    @patch('activity.activity_PackagePOA.storage_context')
    @patch("provider.ejp.EJP.latest_s3_file_name_by_convention")
    @patch('provider.ejp.EJP.ejp_bucket_file_list')
    def test_download_latest_csv(self, fake_ejp_bucket_file_list, fake_by_convention, fake_storage_context):
        "test downloading CSV files from bucket storage"
        # make directories first
        self.poa.make_activity_directories()
        # mock other methods
        fake_storage_context.return_value = FakeStorageContext(directory=self.test_data_dir)
        bucket_list_file = os.path.join("tests", "test_data", "ejp_bucket_list_new.json")
        with open(bucket_list_file, 'rb') as open_file:
            fake_ejp_bucket_file_list.return_value = json.loads(open_file.read().decode())
        fake_by_convention.return_value = None
        # download the CSV files
        self.poa.download_latest_csv()
        # make assertions
        loginfo_message = (
            'CSV file '
            's3://ejp_bucket/ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv'
            ' last_modified: 2021-01-01T00:00:01.000Z')
        self.assertTrue(loginfo_message in self.logger.loginfo)

    @patch('activity.activity_PackagePOA.storage_context')
    @patch('provider.ejp.EJP.find_latest_s3_file_name')
    def test_download_latest_csv_ejp_exception(self, fake_ejp_s3_file_name, fake_storage_context):
        "test exception if CSV file cannot be found using ejp provider"
        # make directories first
        self.poa.make_activity_directories()
        # mock other methods
        fake_storage_context.return_value = FakeStorageContext(directory=self.test_data_dir)
        fake_ejp_s3_file_name.return_value = None
        # download the CSV files
        self.poa.download_latest_csv()
        # make assertions
        loginfo_message = (
            'PackagePoA unable to download CSV file for poa_author')
        self.assertTrue(loginfo_message in self.logger.loginfo)


if __name__ == '__main__':
    unittest.main()
