import unittest
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
        self.ejp = EJP(settings_mock, tmp_dir=self.directory)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @tempdir()
    @patch('provider.filesystem.Filesystem.open_file_from_tmp_dir')
    @patch('provider.filesystem.Filesystem.write_document_to_tmp_dir')
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
    def test_get_authors(self, doi_id, corresponding, expected_authors,
                         fake_filesystem_write, fake_filesystem_open):
        author_csv_file = "tests/test_data/ejp_author_file.csv"
        expected_column_headings = ['ms_no', 'author_seq', 'first_nm', 'last_nm', 'author_type_cde', 'dual_corr_author_ind', 'e_mail']
        # mock things
        fake_filesystem_write = MagicMock()
        authors_fp = open(author_csv_file, 'rb')
        fake_filesystem_open.return_value = authors_fp
        # call the function
        (column_headings, authors) = self.ejp.get_authors(doi_id, corresponding, author_csv_file)
        # assert results
        self.assertEqual(column_headings, expected_column_headings)
        self.assertEqual(authors, expected_authors)
        authors_fp.close()



if __name__ == '__main__':
    unittest.main()
