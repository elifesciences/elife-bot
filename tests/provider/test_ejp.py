# coding=utf-8

import unittest
import json
import os
import arrow
from provider.ejp import EJP
import tests.settings_mock as settings_mock
from testfixtures import tempdir
from testfixtures import TempDirectory
from mock import patch, MagicMock
from ddt import ddt, data, unpack
from tests.activity.classes_mock import FakeBucket


@ddt
class TestProviderEJP(unittest.TestCase):

    def setUp(self):
        self.directory = TempDirectory()
        self.ejp = EJP(settings_mock, tmp_dir=self.directory.path)
        self.author_column_headings = [
            'ms_no', 'author_seq', 'first_nm', 'last_nm', 
            'author_type_cde','dual_corr_author_ind', 'e_mail']
        self.editor_column_headings = ['ms_no', 'first_nm', 'last_nm', 'e_mail']

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

    def test_parse_author_file(self):
        author_csv_file = os.path.join("tests", "test_data", "ejp_author_file.csv")
        # call the function
        (column_headings, authors) = self.ejp.parse_author_file(author_csv_file)
        # assert results
        self.assertEqual(column_headings, self.author_column_headings)

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
        (13, False, [
            ['13', '1', 'Author', 'Uno', 'Contributing Author', ' ', 'author13-01@example.com'],
            ['13', '2', 'Author', 'Dos', 'Contributing Author', ' ', 'author13-02@example.com'],
            ['13', '3', u'Authoré', u'Trés', 'Contributing Author', '1', 'author13-03@example.com'],
            ['13', '4', 'Author', 'Cuatro', 'Corresponding Author', ' ', 'author13-04@example.com']
        ]),
        ("00003", True, [
            ['3', '3', 'Author', 'Three', 'Corresponding Author', ' ', 'author03@example.com']
        ]),
        (666, True, None),
        (None, None, [
            ['3', '1', 'Author', 'One', 'Contributing Author', ' ', 'author01@example.com'], 
            ['3', '2', 'Author', 'Two', 'Contributing Author', ' ', 'author02@example.org'], 
            ['3', '3', 'Author', 'Three', 'Corresponding Author', ' ', 'author03@example.com'], 
            ['13', '1', 'Author', 'Uno', 'Contributing Author', ' ', 'author13-01@example.com'], 
            ['13', '2', 'Author', 'Dos', 'Contributing Author', ' ', 'author13-02@example.com'], 
            ['13', '3', u'Authoré', u'Trés', 'Contributing Author', '1', 'author13-03@example.com'], 
            ['13', '4', 'Author', 'Cuatro', 'Corresponding Author', ' ', 'author13-04@example.com']
        ]),
    )
    @unpack
    def test_get_authors(self, doi_id, corresponding, expected_authors):
        author_csv_file = os.path.join("tests", "test_data", "ejp_author_file.csv")
        # call the function
        (column_headings, authors) = self.ejp.get_authors(doi_id, corresponding, author_csv_file)
        # assert results
        self.assertEqual(column_headings, self.author_column_headings)
        self.assertEqual(authors, expected_authors)

    def test_parse_editor_file(self):
        author_csv_file = os.path.join("tests", "test_data", "ejp_editor_file.csv")
        # call the function
        (column_headings, authors) = self.ejp.parse_editor_file(author_csv_file)
        # assert results
        self.assertEqual(column_headings, self.editor_column_headings)

    @tempdir()
    @data(
        (3, [
            ['3', 'Editor', 'One', 'ed_one@example.com']
        ]),
        ("00003", [
            ['3', 'Editor', 'One', 'ed_one@example.com']
        ]),
        (666, None),
        (None, [
            ['3', 'Editor', 'One', 'ed_one@example.com'],
            ['13', 'Editor', 'Uno', 'ed_uno@example.com']
        ]),
    )
    @unpack
    def test_get_editors(self, doi_id, expected_editors):
        editor_csv_file = os.path.join("tests", "test_data", "ejp_editor_file.csv")
        # call the function
        (column_headings, authors) = self.ejp.get_editors(doi_id, editor_csv_file)
        # assert results
        self.assertEqual(column_headings, self.editor_column_headings)
        self.assertEqual(authors, expected_editors)

    @patch.object(arrow, "utcnow")
    @patch("provider.ejp.EJP.get_bucket")
    @data(
        ('author', 'ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_06_10_eLife.csv'),
        ('editor', 'ejp_query_tool_query_id_15b)_Accepted_Paper_Details_2019_06_10_eLife.csv'),
        ('poa_manuscript', 'ejp_query_tool_query_id_POA_Manuscript_2019_06_10_eLife.csv'),
        ('poa_author', 'ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv'),
        ('poa_license', 'ejp_query_tool_query_id_POA_License_2019_06_10_eLife.csv'),
        ('poa_subject_area', 'ejp_query_tool_query_id_POA_Subject_Area_2019_06_10_eLife.csv'),
        ('poa_received', 'ejp_query_tool_query_id_POA_Received_2019_06_10_eLife.csv'),
        ('poa_research_organism',
         'ejp_query_tool_query_id_POA_Research_Organism_2019_06_10_eLife.csv'),
        ('poa_abstract', 'ejp_query_tool_query_id_POA_Abstract_2019_06_10_eLife.csv'),
        ('poa_title', 'ejp_query_tool_query_id_POA_Title_2019_06_10_eLife.csv'),
        ('poa_keywords', 'ejp_query_tool_query_id_POA_Keywords_2019_06_10_eLife.csv'),
        ('poa_group_authors', 'ejp_query_tool_query_id_POA_Group_Authors_2019_06_10_eLife.csv'),
        ('poa_datasets', 'ejp_query_tool_query_id_POA_Datasets_2019_06_10_eLife.csv'),
        ('poa_funding', 'ejp_query_tool_query_id_POA_Funding_2019_06_10_eLife.csv'),
        ('poa_ethics', 'ejp_query_tool_query_id_POA_Ethics_2019_06_10_eLife.csv'),
    )
    @unpack
    def test_find_latest_s3_file_name_by_convention(self, file_type, expected_s3_key_name, fake_get_bucket, fake_utcnow):
        """test finding latest CSV file names by their expected file name"""
        fake_get_bucket.return_value = FakeBucket()
        fake_utcnow.return_value = arrow.arrow.Arrow(2019, 6, 10)
        # call the function
        s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
        # assert results
        self.assertEqual(s3_key_name, expected_s3_key_name)

    @patch("provider.ejp.EJP.latest_s3_file_name_by_convention")
    @patch('provider.ejp.EJP.ejp_bucket_file_list')
    @data(
        ('author', 'ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_06_10_eLife.csv'),
        ('editor', 'ejp_query_tool_query_id_15b)_Accepted_Paper_Details_2019_06_10_eLife.csv'),
        ('poa_manuscript', 'ejp_query_tool_query_id_POA_Manuscript_2019_06_10_eLife.csv'),
        ('poa_author', 'ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv'),
        ('poa_license', 'ejp_query_tool_query_id_POA_License_2019_06_10_eLife.csv'),
        ('poa_subject_area', 'ejp_query_tool_query_id_POA_Subject_Area_2019_06_10_eLife.csv'),
        ('poa_received', 'ejp_query_tool_query_id_POA_Received_2019_06_10_eLife.csv'),
        ('poa_research_organism',
         'ejp_query_tool_query_id_POA_Research_Organism_2019_06_10_eLife.csv'),
        ('poa_abstract', 'ejp_query_tool_query_id_POA_Abstract_2019_06_10_eLife.csv'),
        ('poa_title', 'ejp_query_tool_query_id_POA_Title_2019_06_10_eLife.csv'),
        ('poa_keywords', 'ejp_query_tool_query_id_POA_Keywords_2019_06_10_eLife.csv'),
        ('poa_group_authors', 'ejp_query_tool_query_id_POA_Group_Authors_2019_06_10_eLife.csv'),
        ('poa_datasets', 'ejp_query_tool_query_id_POA_Datasets_2019_06_10_eLife.csv'),
        ('poa_funding', 'ejp_query_tool_query_id_POA_Funding_2019_06_10_eLife.csv'),
        ('poa_ethics', 'ejp_query_tool_query_id_POA_Ethics_2019_06_10_eLife.csv'),
    )
    @unpack
    def test_find_latest_s3_file_name_new(self, file_type, expected_s3_key_name,
                                          fake_ejp_bucket_file_list, fake_by_convention):
        """from new file naming find the latest CSV file names"""
        fake_by_convention.return_value = None
        bucket_list_file_new = os.path.join("tests", "test_data", "ejp_bucket_list_new.json")
        # mock things
        ejp_bucket_file_list = []
        with open(bucket_list_file_new, 'r') as open_file:
            ejp_bucket_file_list += json.loads(open_file.read())
        fake_ejp_bucket_file_list.return_value = ejp_bucket_file_list
        # call the function
        s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
        # assert results
        self.assertEqual(s3_key_name, expected_s3_key_name)


if __name__ == '__main__':
    unittest.main()
