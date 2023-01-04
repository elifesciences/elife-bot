import unittest
import shutil
import os
import sys
import zipfile
from collections import OrderedDict
from ddt import ddt, data, unpack
from testfixtures import tempdir
from testfixtures import TempDirectory
import provider.article_processing as article_processing
from tests.activity.classes_mock import FakeLogger


@ddt
class TestArticleProcessing(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.file_name_map_19405 = {
            "elife-19405-inf1-v1": "elife-19405-inf1",
            "elife-19405-fig1-v1": "elife-19405-fig1",
            "elife-19405-v1.pdf": "elife-19405.pdf",
            "elife-19405-v1.xml": "elife-19405.xml",
        }

    def tearDown(self):
        TempDirectory.cleanup_all()

    # input: s3 archive zip file name (name) and date last modified
    # expected output: file name - highest version file (displayed on -v[number]-) then latest last modified date/time
    @unpack
    @data(
        {
            "input": [
                {
                    "name": "elife-16747-vor-v1-20160831000000.zip",
                    "last_modified": "2017-05-18T09:04:11.000Z",
                },
                {
                    "name": "elife-16747-vor-v1-20160831132647.zip",
                    "last_modified": "2016-08-31T06:26:56.000Z",
                },
            ],
            "expected": "elife-16747-vor-v1-20160831000000.zip",
        },
        {
            "input": [
                {
                    "name": "elife-16747-vor-v1-20160831000000.zip",
                    "last_modified": "2017-05-18T09:04:11.000Z",
                },
                {
                    "name": "elife-16747-vor-v1-20160831132647.zip",
                    "last_modified": "2016-08-31T06:26:56.000Z",
                },
                {
                    "name": "elife-16747-vor-v2-20160831000000.zip",
                    "last_modified": "2015-01-05T00:20:50.000Z",
                },
            ],
            "expected": "elife-16747-vor-v2-20160831000000.zip",
        },
    )
    def test_latest_archive_zip_revision(self, input, expected):
        output = article_processing.latest_archive_zip_revision(
            "16747", input, "elife", "vor"
        )
        self.assertEqual(output, expected)

    @unpack
    @data(
        {
            "input": [
                {
                    "name": "elife-16747-vor-v2-20160831000000.zip",
                    "last_modified": "this_is_junk_for_testing",
                }
            ],
            "expected": None,
        }
    )
    def test_latest_archive_zip_revision_exception(self, input, expected):
        output = article_processing.latest_archive_zip_revision(
            "16747", input, "elife", "vor"
        )
        self.assertRaises(ValueError)

    def test_convert_xml(self):
        xml_file = "elife-19405-v1.xml"
        file_name_map = self.file_name_map_19405
        expected_xml_contains = "elife-19405.pdf"

        with open("tests/test_data/pmc/" + xml_file, "rb") as fp:
            path = self.directory.write(xml_file, fp.read())
        xml_file_path = os.path.join(self.directory.path, xml_file)

        article_processing.convert_xml(
            xml_file=xml_file_path, file_name_map=file_name_map
        )

        with open(xml_file_path, "r") as fp:
            xml_content = fp.read()
            self.assertTrue(expected_xml_contains in xml_content)

    def test_convert_xml_extra_xml(self):
        xml_file = "tests/test_data/xml_sample_with_directive.xml"
        file_name_map = {}

        with open(xml_file, "rb") as open_file:
            expected = open_file.read()
            path = self.directory.write(xml_file, expected)

        xml_file_path = path

        article_processing.convert_xml(
            xml_file=xml_file_path, file_name_map=file_name_map
        )

        with open(xml_file_path, "rb") as open_file:
            xml_string = open_file.read()
            self.assertEqual(xml_string, expected)

    def test_verify_rename_files(self):
        (
            verified,
            renamed_list,
            not_renamed_list,
        ) = article_processing.verify_rename_files(self.file_name_map_19405)
        self.assertTrue(verified)
        self.assertEqual(len(renamed_list), 4)
        self.assertEqual(len(not_renamed_list), 0)

    def test_verify_rename_files_not_renamed(self):
        (
            verified,
            renamed_list,
            not_renamed_list,
        ) = article_processing.verify_rename_files({"elife-19405-v1.xml": None})
        self.assertFalse(verified)
        self.assertEqual(len(renamed_list), 0)
        self.assertEqual(len(not_renamed_list), 1)

    @data(
        (
            [
                "elife-99999.xml",
                "elife-99999-fig1-v1.tif",
                "elife-99999-video1.mp4",
                "elife-99999-video2.mp4",
            ],
            OrderedDict(
                [
                    ("elife-99999.xml", "elife-99999.xml"),
                    ("elife-99999-fig1-v1.tif", "elife-99999-fig1.tif"),
                    ("elife-99999-video1.mp4", "elife-99999-video1.mp4"),
                    ("elife-99999-video2.mp4", "elife-99999-video2.mp4"),
                ]
            ),
        ),
    )
    @unpack
    def test_stripped_file_name_map(self, file_names, expected_file_name_map):
        file_name_map = article_processing.stripped_file_name_map(file_names)
        self.assertEqual(file_name_map, expected_file_name_map)

    def test_rename_files_remove_version_number(self):
        zip_file = "elife-19405-vor-v1-20160802113816.zip"
        zip_file_path = "tests/test_data/pmc/" + zip_file
        files_dir = "tmp_dir"
        output_dir = "output_didr"
        # create and set directories
        self.directory.makedir(output_dir)
        self.directory.makedir(files_dir)
        files_dir_path = os.path.join(self.directory.path, files_dir)
        output_dir_path = os.path.join(self.directory.path, output_dir)

        # unzip the test data
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            zip_file.extractall(files_dir_path)

        # now can run the function we are testing
        article_processing.rename_files_remove_version_number(
            files_dir_path, output_dir_path
        )

    @unpack
    @data(
        ("elife", "1", "7", None, "elife-01-00007.zip"),
        ("elife", "1", "7", "1", "elife-01-00007.r1.zip"),
    )
    def test_new_pmc_zip_filename(self, journal, volume, fid, revision, expected):
        self.assertEqual(
            article_processing.new_pmc_zip_filename(journal, volume, fid, revision),
            expected,
        )


class TestRepackageArchiveZip(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_repackage_archive_zip_to_pmc_zip(self):
        directory = TempDirectory()
        logger = FakeLogger()
        input_zip_file_path = (
            "tests/test_data/pmc/elife-19405-vor-v1-20160802113816.zip"
        )
        journal = "elife"
        volume = 5
        doi_id = 19405
        new_zip_file_name = article_processing.new_pmc_zip_filename(
            journal, volume, doi_id
        )

        # make the input_dir and output_dir for the tests
        input_dir = os.path.join(directory.path, "input_dir")
        os.makedirs(input_dir, exist_ok=True)
        output_dir = os.path.join(directory.path, "output_dir")
        os.makedirs(output_dir, exist_ok=True)

        new_zip_file_path = os.path.join(output_dir, new_zip_file_name)

        temp_dir = os.path.join(directory.path, "temp_dir")
        zip_renamed_files_dir = os.path.join(temp_dir, "rename_dir")

        expected_pmc_zip_file = os.path.join(output_dir, new_zip_file_name)
        expected_article_xml_file = os.path.join(
            zip_renamed_files_dir, "elife-19405.xml"
        )
        expected_article_xml_string = b"elife-19405.pdf"
        expected_file_name_map = OrderedDict(
            [
                ("elife-19405-fig1-v1.tif", "elife-19405-fig1.tif"),
                ("elife-19405-inf1-v1.tif", "elife-19405-inf1.tif"),
                ("elife-19405-v1.pdf", "elife-19405.pdf"),
                ("elife-19405-v1.xml", "elife-19405.xml"),
            ]
        )
        expected_pmc_zip_file_contents = expected_file_name_map.values()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            input_dir,
            input_zip_file_path.rsplit("/", 1)[-1],
        )
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        article_processing.repackage_archive_zip_to_pmc_zip(
            input_zip_file_path,
            new_zip_file_path,
            temp_dir,
            logger,
            alter_xml=True,
            remove_version_doi=True,
        )
        # now can check the results
        self.assertTrue(os.path.exists(expected_pmc_zip_file))
        self.assertTrue(os.path.exists(expected_article_xml_file))
        with open(expected_article_xml_file, "rb") as open_file:
            # check for a renamed file in the XML contents
            self.assertTrue(expected_article_xml_string in open_file.read())
        with zipfile.ZipFile(expected_pmc_zip_file) as zip_file:
            # check pmc zip file contents
            self.assertEqual(
                sorted(zip_file.namelist()), sorted(expected_pmc_zip_file_contents)
            )
        # check for log messages
        self.assertEqual(
            logger.loginfo[1],
            (
                "repackage_archive_zip_to_pmc_zip() verified renamed files from %s: True"
                % input_zip_file_path.rsplit("/", 1)[-1]
            ),
        )
        self.assertEqual(
            logger.loginfo[2],
            ("renamed: %s" % sorted(list(expected_file_name_map.keys()))),
        )
        self.assertEqual(
            logger.loginfo[3],
            ("file_name_map: %s" % expected_file_name_map),
        )

    def test_retain_version_number(self):
        "test not removing version number from file names"
        directory = TempDirectory()
        logger = FakeLogger()
        input_zip_file_path = (
            "tests/test_data/pmc/elife-19405-vor-v1-20160802113816.zip"
        )
        journal = "elife"
        volume = 5
        doi_id = 19405
        new_zip_file_name = article_processing.new_pmc_zip_filename(
            journal, volume, doi_id
        )

        # make the input_dir and output_dir for the tests
        input_dir = os.path.join(directory.path, "input_dir")
        os.makedirs(input_dir, exist_ok=True)
        output_dir = os.path.join(directory.path, "output_dir")
        os.makedirs(output_dir, exist_ok=True)

        new_zip_file_path = os.path.join(output_dir, new_zip_file_name)

        temp_dir = os.path.join(directory.path, "temp_dir")
        expanded_files_dir = os.path.join(temp_dir, "junk_dir")

        expected_pmc_zip_file = os.path.join(output_dir, new_zip_file_name)
        expected_article_xml_file = os.path.join(
            expanded_files_dir, "elife-19405-v1.xml"
        )
        expected_article_xml_string = b"elife-19405-v1.pdf"
        expected_file_name_map = OrderedDict(
            [
                ("elife-19405-fig1-v1.tif", "elife-19405-fig1-v1.tif"),
                ("elife-19405-inf1-v1.tif", "elife-19405-inf1-v1.tif"),
                ("elife-19405-v1.pdf", "elife-19405-v1.pdf"),
                ("elife-19405-v1.xml", "elife-19405-v1.xml"),
            ]
        )
        expected_pmc_zip_file_contents = expected_file_name_map.values()
        # copy in some sample data
        dest_input_zip_file_path = os.path.join(
            input_dir,
            input_zip_file_path.rsplit("/", 1)[-1],
        )
        shutil.copy(input_zip_file_path, dest_input_zip_file_path)
        article_processing.repackage_archive_zip_to_pmc_zip(
            input_zip_file_path,
            new_zip_file_path,
            temp_dir,
            logger,
            alter_xml=True,
            remove_version_doi=True,
            retain_version_number=True,
        )
        # now can check the results
        self.assertTrue(os.path.exists(expanded_files_dir))
        self.assertTrue(os.path.exists(expected_article_xml_file))
        with open(expected_article_xml_file, "rb") as open_file:
            # check for a renamed file in the XML contents
            self.assertTrue(expected_article_xml_string in open_file.read())
        with zipfile.ZipFile(expected_pmc_zip_file) as zip_file:
            # check pmc zip file contents
            self.assertEqual(
                sorted(zip_file.namelist()), sorted(expected_pmc_zip_file_contents)
            )
        # check for log messages
        self.assertEqual(
            logger.loginfo[1],
            (
                "not removing version number in files from %s"
                % input_zip_file_path.rsplit("/", 1)[-1]
            ),
        )
        self.assertEqual(
            logger.loginfo[2],
            ("file_name_map: %s" % expected_file_name_map),
        )


class TestAlterXML(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_alter_xml_unchanged(self):
        "test altering a file where no changes will be made, output is the same as input"
        directory = TempDirectory()
        filename = "elife-00353-v1.xml"
        source_file = "tests/files_source/%s" % filename
        test_file = os.path.join(directory.path, filename)
        shutil.copy(source_file, test_file)
        article_processing.alter_xml_related_object(test_file, self.logger)
        with open(source_file, "r", encoding="utf-8") as open_file:
            with open(test_file, "r", encoding="utf-8") as open_output_file:
                altered_xml = open_output_file.read()
                expected = open_file.read()
                # in Python 3.8 or newer the XML attributes will be a different order
                if sys.version_info >= (3, 8):
                    expected = expected.replace(
                        '<article article-type="discussion" dtd-version="1.1d3" xmlns:xlink="http://www.w3.org/1999/xlink">',
                        '<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="discussion" dtd-version="1.1d3">',
                    )
                self.assertEqual(altered_xml, expected)

    def test_alter_xml(self):
        "test an example XML"
        directory = TempDirectory()
        xml_declaration = """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD with MathML3 v1.2 20190208//EN"  "JATS-archivearticle1-mathml3.dtd">"""
        xml_string = (
            """%s<article xmlns:xlink="http://www.w3.org/1999/xlink">
<sub-article>
<front-stub>
<related-object id="sa0ro1" link-type="continued-by" object-id="10.1101/2021.02.28.433255" object-id-type="id" xlink:href="https://sciety.org/articles/activity/10.1101/2021.02.28.433255"/>
</front-stub>
</sub-article>
</article>"""
            % xml_declaration
        )
        if sys.version_info < (3, 8):
            expected = (
                """%s<article xmlns:xlink="http://www.w3.org/1999/xlink">
<sub-article>
<front-stub>
<ext-link ext-link-type="uri" id="sa0ro1" xlink:href="https://sciety.org/articles/activity/10.1101/2021.02.28.433255"/>
</front-stub>
</sub-article>
</article>"""
                % xml_declaration
            )
        else:
            # ext-link-type attribute will be last in Python 3.8 or newer
            expected = (
                """%s<article xmlns:xlink="http://www.w3.org/1999/xlink">
<sub-article>
<front-stub>
<ext-link id="sa0ro1" xlink:href="https://sciety.org/articles/activity/10.1101/2021.02.28.433255" ext-link-type="uri"/>
</front-stub>
</sub-article>
</article>"""
                % xml_declaration
            )

        filename = "elife-99999-v1.xml"
        test_file = os.path.join(directory.path, filename)
        with open(test_file, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        article_processing.alter_xml_related_object(test_file, self.logger)
        with open(test_file, "r", encoding="utf-8") as open_file:
            self.assertEqual(open_file.read(), expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            "Converting related-object tag to ext-link tag in sub-article",
        )


class TestRemoveVersionDoiTag(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_remove_version_doi_tag_unchanged(self):
        "test altering a file where no changes will be made, output is the same as input"
        directory = TempDirectory()
        filename = "elife-00353-v1.xml"
        source_file = "tests/files_source/%s" % filename
        test_file = os.path.join(directory.path, filename)
        shutil.copy(source_file, test_file)
        article_processing.remove_version_doi_tag(test_file, self.logger)
        with open(source_file, "r", encoding="utf-8") as open_file:
            with open(test_file, "r", encoding="utf-8") as open_output_file:
                altered_xml = open_output_file.read()
                expected = open_file.read()
                # in Python 3.8 or newer the XML attributes will be a different order
                if sys.version_info >= (3, 8):
                    expected = expected.replace(
                        '<article article-type="discussion" dtd-version="1.1d3" xmlns:xlink="http://www.w3.org/1999/xlink">',
                        '<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="discussion" dtd-version="1.1d3">',
                    )
                self.assertEqual(altered_xml, expected)

    def test_remove_version_doi_tag(self):
        "test an example XML"
        directory = TempDirectory()
        xml_declaration = """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD with MathML3 v1.2 20190208//EN"  "JATS-archivearticle1-mathml3.dtd">"""
        xml_string = (
            """%s<article xmlns:xlink="http://www.w3.org/1999/xlink">
<front>
<article-meta>
<article-id pub-id-type="publisher-id">1234567890</article-id>
<article-id pub-id-type="doi">10.7554/eLife.1234567890</article-id>
<article-id pub-id-type="doi" specific-use="version">10.7554/eLife.1234567890.4</article-id>
</article-meta>
</front>
</article>"""
            % xml_declaration
        )

        expected = (
            """%s<article>
<front>
<article-meta>
<article-id pub-id-type="publisher-id">1234567890</article-id>
<article-id pub-id-type="doi">10.7554/eLife.1234567890</article-id>
</article-meta>
</front>
</article>"""
            % xml_declaration
        )

        filename = "elife-99999-v1.xml"
        test_file = os.path.join(directory.path, filename)
        with open(test_file, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        article_processing.remove_version_doi_tag(test_file, self.logger)
        with open(test_file, "r", encoding="utf-8") as open_file:
            self.assertEqual(open_file.read(), expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            "Removing version DOI article-id tag",
        )


if __name__ == "__main__":
    unittest.main()
