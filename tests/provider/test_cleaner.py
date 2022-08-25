import os
import unittest
from collections import OrderedDict
import zipfile
from mock import patch
from testfixtures import TempDirectory
import wand
from provider import cleaner
from tests import settings_mock
from tests.activity.classes_mock import FakeStorageContext


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


class TestParseArticleXml(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.logfile = os.path.join(self.directory.path, "elifecleaner.log")
        cleaner.log_to_file(self.logfile)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_parse_article_xml(self):
        xml_file_path = os.path.join(self.directory.path, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write(
                "<article><title>To &#x001D;nd odd entities.</title></article>"
            )
        cleaner.parse_article_xml(xml_file_path)
        with open(self.logfile, "r") as open_file:
            self.assertEqual(
                open_file.readline(),
                (
                    "INFO elifecleaner:parse:parse_article_xml: Replacing character entities "
                    "in the XML string: ['&#x001D;']\n"
                ),
            )


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


class TestBucketAssetFileNameMap(unittest.TestCase):
    @patch.object(FakeStorageContext, "list_resources")
    @patch.object(cleaner, "storage_context")
    def test_bucket_asset_file_name_map(
        self, fake_storage_context, fake_list_resources
    ):
        fake_storage_context.return_value = FakeStorageContext()
        bucket_name = "bucket"
        expanded_folder = "expanded_folder/folder/99999/run/expanded_files"
        fake_list_resources.return_value = ["%s/article/article.xml" % expanded_folder]
        expected = {
            "article/article.xml": "s3://%s/%s/article/article.xml"
            % (bucket_name, expanded_folder)
        }
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            settings_mock, bucket_name, expanded_folder
        )
        self.assertEqual(asset_file_name_map, expected)


class TestProductionComments(unittest.TestCase):
    def setUp(self):
        self.cleaner_log = (
            "2022-03-31 11:11:39,632 INFO elifecleaner:parse:check_multi_page_figure_pdf: "
            "12-08-2021-RA-eLife-73010.zip using pdfimages to check PDF figure file: 12-08-2021-RA-eLife-73010/Figure 1.pdf\n"
            "2022-03-31 11:11:39,705 INFO elifecleaner:parse:check_multi_page_figure_pdf: 12-08-2021-RA-eLife-73010.zip pdfimages found images on pages {1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14} in PDF figure file: 12-08-2021-RA-eLife-73010/Figure 1.pdf\n"
            "2022-03-31 11:11:39,706 WARNING elifecleaner:parse:check_multi_page_figure_pdf: 12-08-2021-RA-eLife-73010.zip multiple page PDF figure file: 12-08-2021-RA-eLife-73010/Figure 1.pdf\n"
            "2022-03-17 11:10:06,722 WARNING elifecleaner:parse:check_missing_files: 20-12-2021-FA-eLife-76559.zip does not contain a file in the manifest: manuscript.tex\n"
            "2022-03-17 11:10:06,722 WARNING elifecleaner:parse:check_extra_files: 20-12-2021-FA-eLife-76559.zip has file not listed in the manifest: 76559 correct version.tex\n"
            "2022-02-22 13:10:15,942 WARNING elifecleaner:parse:check_missing_files_by_name: 22-02-2022-CR-eLife-78088.zip has file missing from expected numeric sequence: Figure 3\n"
            "2022-02-22 13:10:15,942 WARNING elifecleaner:parse:check_art_file: 22-02-2022-CR-eLife-78088.zip could not find a word or latex article file in the package\n"
            "2022-06-29 13:10:15,942 INFO elifecleaner:transform:transform_xml_funding: 22-02-2022-CR-eLife-78088.zip adding the WELLCOME_FUNDING_STATEMENT to the funding-statement\n"
            "2022-06-29 13:10:15,942 INFO elifecleaner:parse:parse_article_xml: Replacing character entities in the XML string: ['&#x001D;']\n"
            "2022-06-29 13:10:15,942 INFO elifecleaner:video:all_terms_map: found duplicate video term values\n"
            "2022-06-29 13:10:15,942 INFO elifecleaner:video:renumber: duplicate values: ['fig1video2']\n"
            "2022-06-29 13:10:15,942 INFO elifecleaner:video:renumber_term_map: replacing number 2 with 3 for term Supplementary Video 2.mp4\n"
        )

    def test_production_comments(self):
        expected = [
            'Exeter: "Figure 1.pdf" is a PDF file made up of more than one page. Please check if there are images on numerous pages. If that\'s the case, please add the following author query: "Please provide this figure in a single-page format. If this would render the figure unreadable, please provide this as separate figures or figure supplements."',
            "20-12-2021-FA-eLife-76559.zip does not contain a file in the manifest: manuscript.tex",
            "20-12-2021-FA-eLife-76559.zip has file not listed in the manifest: 76559 correct version.tex",
            "22-02-2022-CR-eLife-78088.zip has file missing from expected numeric sequence: Figure 3",
            "22-02-2022-CR-eLife-78088.zip could not find a word or latex article file in the package",
            cleaner.WELLCOME_FUNDING_COMMENTS,
            "Replacing character entities in the XML string: ['&#x001D;']",
            "found duplicate video term values",
            "duplicate values: ['fig1video2']",
            "replacing number 2 with 3 for term Supplementary Video 2.mp4",
        ]

        comments = cleaner.production_comments(self.cleaner_log)
        self.assertEqual(comments, expected)

    def test_production_comments_for_xml(self):
        "will not include the check_art_file log message in the XML comments returned"
        expected = [
            'Exeter: "Figure 1.pdf" is a PDF file made up of more than one page. Please check if there are images on numerous pages. If that\'s the case, please add the following author query: "Please provide this figure in a single-page format. If this would render the figure unreadable, please provide this as separate figures or figure supplements."',
            "20-12-2021-FA-eLife-76559.zip does not contain a file in the manifest: manuscript.tex",
            "20-12-2021-FA-eLife-76559.zip has file not listed in the manifest: 76559 correct version.tex",
            "22-02-2022-CR-eLife-78088.zip has file missing from expected numeric sequence: Figure 3",
            cleaner.WELLCOME_FUNDING_COMMENTS,
        ]

        comments = cleaner.production_comments_for_xml(self.cleaner_log)
        self.assertEqual(comments, expected)
