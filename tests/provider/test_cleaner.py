import os
import unittest
from collections import OrderedDict
import zipfile
from mock import patch
from testfixtures import TempDirectory
import wand
from provider import cleaner


class TestCleanerProvider(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.logfile = os.path.join(self.directory.path, "elifecleaner.log")
        cleaner.log_to_file(self.logfile)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_pdf_page_count(self):
        file_path = "tests/files_source/elife-00353-v1.pdf"
        page_count = cleaner.parse.pdf_page_count(file_path)
        self.assertEqual(page_count, 2)

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_exception(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.WandRuntimeError()
        file_path = "tests/files_source/elife-00353-v1.pdf"
        with self.assertRaises(wand.exceptions.WandRuntimeError):
            page_count = cleaner.parse.pdf_page_count(file_path)
        with open(self.logfile, "r") as open_file:
            self.assertEqual(
                open_file.readline(),
                (
                    "ERROR elifecleaner:parse:pdf_page_count: WandRuntimeError "
                    "in pdf_page_count(), imagemagick may not be installed\n"
                ),
            )


class TestArticleIdFromZipFile(unittest.TestCase):
    def test_article_id_from_zip_file(self):
        "test common file name"
        zip_file = "30-01-2019-RA-eLife-45644.zip"
        expected = "45644"
        self.assertEqual(cleaner.article_id_from_zip_file(zip_file), expected)

    def test_article_id_from_zip_file_path(self):
        "test if there are subfolders in the path"
        zip_file = "folder1/folder2/30-01-2019-RA-eLife-45644.zip"
        expected = "45644"
        self.assertEqual(cleaner.article_id_from_zip_file(zip_file), expected)

    def test_article_id_from_zip_file_revision_number(self):
        "test file name with R1 in it"
        zip_file = "30-01-2019-RA-eLife-45644R1.zip"
        expected = "45644"
        self.assertEqual(cleaner.article_id_from_zip_file(zip_file), expected)

    def test_article_id_from_zip_file_unknown(self):
        "test something which does not match the regular expression"
        zip_file = "unknown.zip"
        expected = "unknown.zip"
        self.assertEqual(cleaner.article_id_from_zip_file(zip_file), expected)


class TestArticleXmlAsset(unittest.TestCase):
    def test_article_xml_asset(self):
        xml_file = "article/article.xml"
        xml_path = "tmp/article/article.xml"
        asset_file_name_map = {
            xml_file: xml_path,
            "article/article.pdf": "tmp/article/article.pdf",
        }
        expected = (xml_file, xml_path)
        self.assertEqual(cleaner.article_xml_asset(asset_file_name_map), expected)

    def test_article_xml_asset_none(self):
        asset_file_name_map = {}
        expected = None
        self.assertEqual(cleaner.article_xml_asset(asset_file_name_map), expected)


class TestFileList(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_file_list(self):
        "extract the XML file from a zip file to parse it and get the file_list"
        directory = TempDirectory()
        zip_file_path = os.path.join(
            "tests", "files_source", "30-01-2019-RA-eLife-45644.zip"
        )
        xml_file_name = "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
        with zipfile.ZipFile(zip_file_path, "r") as open_zip:
            open_zip.extract(xml_file_name, directory.path)
        xml_file_path = os.path.join(directory.path, xml_file_name)
        files = cleaner.file_list(xml_file_path)
        self.assertEqual(len(files), 41)
        self.assertEqual(
            files[0],
            OrderedDict(
                [
                    ("file_type", "merged_pdf"),
                    ("id", "1128853"),
                    ("upload_file_nm", "30-01-2019-RA-eLife-45644.pdf"),
                    ("custom_meta", []),
                ]
            ),
        )


class TestFilesByExtension(unittest.TestCase):
    def test_files_by_extension(self):
        "filter the list based on the file name extension"
        # an abbreviated files list for testing
        files = [
            OrderedDict(
                [
                    ("upload_file_nm", "30-01-2019-RA-eLife-45644.pdf"),
                ],
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "30-01-2019-RA-eLife-45644.xml"),
                ],
            ),
        ]
        expected = [OrderedDict([("upload_file_nm", "30-01-2019-RA-eLife-45644.pdf")])]
        filtered_files = cleaner.files_by_extension(files, "pdf")
        self.assertEqual(filtered_files, expected)
