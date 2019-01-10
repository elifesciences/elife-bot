import unittest
import json
import os
from provider.ejp import EJP
import tests.settings_mock as settings_mock
from testfixtures import tempdir
from testfixtures import TempDirectory
from mock import patch, MagicMock
from ddt import ddt, data, unpack

@ddt
class TestProviderEJP(unittest.TestCase):

    def setUp(self):
        self.directory = TempDirectory()
        self.ejp = EJP(settings_mock, tmp_dir=self.directory.path)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @tempdir()
    @data(
        (None, '', 'wb', TypeError, None),
        ('read_mode_failure.txt', '', 'r', IOError, None),
        ('good.txt', 'good', 'wb', None, 'good.txt'),
    )
    @unpack
    def test_write_content_to_file(self, filename, content, mode, exception_raised, expected_document):
        # if we expect a document, for comparison we need to add the tmp_dir path to it
        if expected_document:
            expected_document = os.path.join(self.directory.path, expected_document)
        try:
            document = self.ejp.write_content_to_file(filename, content, mode)
            # check the returned value
            self.assertEqual(document, expected_document)
        except:
            # check the exception
            if exception_raised:
                self.assertRaises(exception_raised)


    @tempdir()
    @data(
        (3, False, [
            ['3', '1', 'Author', 'One', 'Contributing Author', ' ', 'author01@example.com'],
            ['3', '2', 'Author', 'Two', 'Contributing Author', ' ', 'author02@example.org'],
            ['3', '3', 'Author', 'Three', 'Corresponding Author', ' ', 'author03@example.com']
        ]),
        (3, True, [
            ['3', '3', 'Author', 'Three', 'Corresponding Author', ' ', 'author03@example.com']
        ]),
        (666, True, None),
    )
    @unpack
    def test_get_authors(self, doi_id, corresponding, expected_authors):
        author_csv_file = os.path.join("tests", "test_data", "ejp_author_file.csv")
        expected_column_headings = ['ms_no', 'author_seq', 'first_nm', 'last_nm', 'author_type_cde', 'dual_corr_author_ind', 'e_mail']
        # call the function
        (column_headings, authors) = self.ejp.get_authors(doi_id, corresponding, author_csv_file)
        # assert results
        self.assertEqual(column_headings, expected_column_headings)
        self.assertEqual(authors, expected_authors)


    @tempdir()
    @data(
        (3, [
            ['3', 'Editor', 'One', 'ed_one@example.com']
        ]),
        (666, None),
    )
    @unpack
    def test_get_editors(self, doi_id, expected_editors):
        editor_csv_file = os.path.join("tests", "test_data", "ejp_editor_file.csv")
        expected_column_headings = ['ms_no', 'first_nm', 'last_nm', 'e_mail']
        # call the function
        (column_headings, authors) = self.ejp.get_editors(doi_id, editor_csv_file)
        # assert results
        self.assertEqual(column_headings, expected_column_headings)
        self.assertEqual(authors, expected_editors)


    @tempdir()
    @patch('provider.ejp.EJP.ejp_bucket_file_list')
    @data(
        ('author', 'ejp_query_tool_query_id_152_15a)_Accepted_Paper_Details_2013_10_31_eLife.csv'),
        ('editor', 'ejp_query_tool_query_id_158_15b)_Accepted_Paper_Details_2013_10_31_eLife.csv'),
        ('poa_manuscript', 'ejp_query_tool_query_id_176_POA_Manuscript_2014_03_19_eLife.csv'),
        ('poa_author', 'ejp_query_tool_query_id_177_POA_Author_2014_03_19_eLife.csv'),
        ('poa_license', 'ejp_query_tool_query_id_178_POA_License_2014_03_19_eLife.csv'),
        ('poa_subject_area', 'ejp_query_tool_query_id_179_POA_Subject_Area_2014_03_19_eLife.csv'),
        ('poa_received', 'ejp_query_tool_query_id_180_POA_Received_2014_03_19_eLife.csv'),
        ('poa_research_organism', 'ejp_query_tool_query_id_182_POA_Research_Organism_2014_03_19_eLife.csv'),
    )
    @unpack
    def test_find_latest_s3_file_name(self, file_type, expected_s3_key_name,
                         fake_ejp_bucket_file_list):
        bucket_list_file = os.path.join("tests", "test_data", "ejp_bucket_list.json")
        # mock things
        with open(bucket_list_file, 'r') as fp:
            fake_ejp_bucket_file_list.return_value = json.loads(fp.read())
        # call the function
        s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
        # assert results
        self.assertEqual(s3_key_name, expected_s3_key_name)




if __name__ == '__main__':
    unittest.main()
