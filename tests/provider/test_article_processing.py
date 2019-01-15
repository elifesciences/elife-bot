import unittest
import os
import zipfile
from ddt import ddt, data, unpack
from testfixtures import tempdir
from testfixtures import TempDirectory
import provider.article_processing as article_processing


@ddt
class TestArticleProcessing(unittest.TestCase):

    def setUp(self):
        self.directory = TempDirectory()
        self.file_name_map_19405 = {
            "elife-19405-inf1-v1": "elife-19405-inf1",
            "elife-19405-fig1-v1": "elife-19405-fig1",
            "elife-19405-v1.pdf": "elife-19405.pdf",
            "elife-19405-v1.xml": "elife-19405.xml"
        }

    def tearDown(self):
        TempDirectory.cleanup_all()

    # input: s3 archive zip file name (name) and date last modified
    # expected output: file name - highest version file (displayed on -v[number]-) then latest last modified date/time
    @unpack
    @data({"input": [{"name": "elife-16747-vor-v1-20160831000000.zip", "last_modified": "2017-05-18T09:04:11.000Z"},
                    {"name": "elife-16747-vor-v1-20160831132647.zip", "last_modified": "2016-08-31T06:26:56.000Z"}],
           "expected": "elife-16747-vor-v1-20160831000000.zip"},
          {"input": [{"name": "elife-16747-vor-v1-20160831000000.zip", "last_modified": "2017-05-18T09:04:11.000Z"},
                    {"name": "elife-16747-vor-v1-20160831132647.zip", "last_modified": "2016-08-31T06:26:56.000Z"},
                    {"name": "elife-16747-vor-v2-20160831000000.zip", "last_modified": "2015-01-05T00:20:50.000Z"}],
           "expected": "elife-16747-vor-v2-20160831000000.zip"}
          )
    def test_latest_archive_zip_revision(self, input, expected):
        output = article_processing.latest_archive_zip_revision("16747", input, "elife", "vor")
        self.assertEqual(output, expected)

    @unpack
    @data(
          {"input": [{"name": "elife-16747-vor-v2-20160831000000.zip", "last_modified": "this_is_junk_for_testing"}],
           "expected": None}
          )
    def test_latest_archive_zip_revision_exception(self, input, expected):
        output = article_processing.latest_archive_zip_revision("16747", input, "elife", "vor")
        self.assertRaises(ValueError)


    def test_convert_xml(self):
        xml_file = 'elife-19405-v1.xml'
        file_name_map = self.file_name_map_19405
        expected_xml_contains = 'elife-19405.pdf'

        with open('tests/test_data/pmc/' + xml_file, 'rb') as fp:
            path = self.directory.write(xml_file, fp.read())
        xml_file_path = os.path.join(self.directory.path, xml_file)

        article_processing.convert_xml(
            xml_file = xml_file_path,
            file_name_map = file_name_map)

        with open(xml_file_path, 'r') as fp:
            xml_content = fp.read()
            self.assertTrue(expected_xml_contains in xml_content)


    def test_verify_rename_files(self):
        verified, renamed_list, not_renamed_list = article_processing.verify_rename_files(
            self.file_name_map_19405)
        self.assertTrue(verified)
        self.assertEqual(len(renamed_list), 4)
        self.assertEqual(len(not_renamed_list), 0)


    def test_verify_rename_files_not_renamed(self):
        verified, renamed_list, not_renamed_list = article_processing.verify_rename_files(
            {'elife-19405-v1.xml': None})
        self.assertFalse(verified)
        self.assertEqual(len(renamed_list), 0)
        self.assertEqual(len(not_renamed_list), 1)


    def test_rename_files_remove_version_number(self):
        zip_file = 'elife-19405-vor-v1-20160802113816.zip'
        zip_file_path = 'tests/test_data/pmc/' + zip_file
        files_dir = 'tmp_dir'
        output_dir = 'output_didr'
        # create and set directories
        self.directory.makedir(output_dir)
        self.directory.makedir(files_dir)
        files_dir_path = os.path.join(self.directory.path, files_dir)
        output_dir_path = os.path.join(self.directory.path, output_dir)

        # unzip the test data
        with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
            zip_file.extractall(files_dir_path)

        # now can run the function we are testing
        article_processing.rename_files_remove_version_number(files_dir_path, output_dir_path)


    @unpack
    @data(
        ('elife', '1', '7', None, 'elife-01-00007.zip'),
        ('elife', '1', '7', '1', 'elife-01-00007.r1.zip')
    )
    def test_new_pmc_zip_filename(self, journal, volume, fid, revision, expected):
        self.assertEqual(article_processing.new_pmc_zip_filename(
            journal, volume, fid, revision), expected)



if __name__ == '__main__':
    unittest.main()
