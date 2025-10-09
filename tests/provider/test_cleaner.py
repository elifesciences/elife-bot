import os
import json
import time
import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from collections import OrderedDict
import zipfile
from mock import patch
from testfixtures import TempDirectory
import wand
from elifearticle.article import Dataset
from provider import cleaner
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext


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

    def test_malformed_xml(self):
        "test XML missing a namespace will raise an exception"
        xml_file_path = os.path.join(self.directory.path, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write(
                "<article><title>To &#x001D;nd odd entities.</title>"
                '<p>A <ext-link xlink:href="https://example.org/">link</ext-link>.</article>'
            )
        with self.assertRaises(ParseError):
            cleaner.parse_article_xml(xml_file_path)
        with open(self.logfile, "r") as open_file:
            log_contents = open_file.read()
        log_lines = [line for line in log_contents.split("\n")]
        self.assertEqual(
            log_lines[0],
            (
                "INFO elifecleaner:parse:parse_article_xml: Replacing character entities "
                "in the XML string: ['&#x001D;']"
            ),
        )
        # if REPAIR_XML = False
        # self.assertEqual(
        #    log_lines[1],
        #    (
        #        "ERROR elifecleaner:parse:parse_article_xml: "
        #        "ParseError raised because REPAIR_XML flag is False"
        #    ),
        # )


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


class TestIsPrc(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_is_prc(self):
        "the standard test fixture is not PRC"
        directory = TempDirectory()
        zip_file_name = "30-01-2019-RA-eLife-45644.zip"
        zip_file_path = os.path.join("tests", "files_source", zip_file_name)
        xml_file_name = "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
        with zipfile.ZipFile(zip_file_path, "r") as open_zip:
            open_zip.extract(xml_file_name, directory.path)
        xml_file_path = os.path.join(directory.path, xml_file_name)
        result = cleaner.is_prc(xml_file_path, zip_file_name)
        self.assertEqual(result, False)

    def test_is_prc_by_zip_file(self):
        "test a zip file name for PRC status"
        zip_file_name = "30-01-2019-RP-RA-eLife-45644.zip"
        xml_file_path = None
        result = cleaner.is_prc(xml_file_path, zip_file_name)
        self.assertEqual(result, True)

    def test_is_prc_by_xml(self):
        "test when the XML indicates it is PRC status"
        directory = TempDirectory()
        zip_file_name = "test.zip"
        xml_file_name = "test.xml"
        xml_string = (
            "<article><front><journal-meta>"
            '<journal-id journal-id-type="publisher-id">foo</journal-id><issn>2050-084X</issn>'
            "</journal-meta></front></article>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        result = cleaner.is_prc(xml_file_path, zip_file_name)
        self.assertEqual(result, True)


class TestTransformPrc(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_transform_prc(self):
        "test modifying the XML for a PRC article"
        directory = TempDirectory()
        zip_file_name = "test.zip"
        xml_file_name = "test.xml"
        xml_string = (
            "<article>"
            "<front>"
            "<journal-meta>"
            '<journal-id journal-id-type="publisher-id">foo</journal-id>'
            "<journal-title-group>"
            "<journal-title>eLife Reviewed Preprints </journal-title>"
            "</journal-title-group>"
            "<issn>2050-084X</issn>"
            "<publisher>"
            "<publisher-name>elife-rp Sciences Publications, Ltd</publisher-name>"
            "</publisher>"
            "</journal-meta>"
            "<article-meta>"
            "<elocation-id>e1234567890</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        cleaner.transform_prc(xml_file_path, zip_file_name)
        # check output
        with open(xml_file_path, "r") as open_file:
            xml_contents = open_file.read()
        self.assertTrue(
            '<journal-id journal-id-type="publisher-id">eLife</journal-id>'
            in xml_contents
        )
        self.assertTrue("<journal-title>eLife</journal-title>" in xml_contents)
        self.assertTrue(
            "<publisher-name>eLife Sciences Publications, Ltd</publisher-name>"
            in xml_contents
        )
        self.assertTrue(
            (
                "<custom-meta-group>"
                '<custom-meta specific-use="meta-only">'
                "<meta-name>publishing-route</meta-name>"
                "<meta-value>prc</meta-value>"
                "</custom-meta>"
                "</custom-meta-group>"
            )
            in xml_contents
        )


class TestPreprintUrl(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_preprint_url(self):
        "test modifying the XML for a PRC article"
        directory = TempDirectory()
        xml_file_name = "test.xml"

        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            '<fn-group content-type="article-history">'
            "<title>Preprint</title>"
            '<fn fn-type="other"/>'
            '<ext-link ext-link-type="url" xlink:href="https://doi.org/10.1101/2021.06.02.446694"/>'
            "</fn-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = "https://doi.org/10.1101/2021.06.02.446694"
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.preprint_url(xml_file_path)
        # check output
        self.assertEqual(result, expected)

    def test_preprint_url_none(self):
        "test not finding a preprint_url"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        xml_string = "<article />"
        expected = None
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.preprint_url(xml_file_path)
        # check output
        self.assertEqual(result, expected)


class TestInlineGraphicTags(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_inline_graphic_tags(self):
        "test modifying the XML for a PRC article"
        directory = TempDirectory()
        xml_file_name = "test.xml"

        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<sub-article>"
            "<body><p>"
            '<inline-graphic xlink:href="https://example.org/image1.jpg" />'
            '<inline-graphic xlink:href="https://example.org/image2.jpg" />'
            "</p></body>"
            "</sub-article>"
            "</article>"
        )
        expected_result_len = 2
        expected_tag_0_string = (
            '<inline-graphic xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xlink:href="https://example.org/image1.jpg" />'
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.inline_graphic_tags(xml_file_path)
        # check output
        self.assertEqual(len(result), expected_result_len)
        self.assertEqual(
            ElementTree.tostring(result[0]).decode("utf8"), expected_tag_0_string
        )

    def test_inline_graphic_tags_none(self):
        "test not finding a preprint_url"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        xml_string = "<article />"
        expected = []
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.inline_graphic_tags(xml_file_path)
        # check output
        self.assertEqual(result, expected)


class TestTableWrapGraphicTags(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_table_wrap_graphic_tags(self):
        "test finding graphic tags inside table-wrap tags"
        directory = TempDirectory()
        xml_file_name = "test.xml"

        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<sub-article>"
            "<body><p>"
            '<graphic xlink:href="https://example.org/image1.jpg" />'
            "<table-wrap>"
            '<graphic xlink:href="https://example.org/image2.jpg" />'
            "</table-wrap>"
            "</p></body>"
            "</sub-article>"
            "</article>"
        )
        expected_result_len = 1
        expected_tag_0_string = (
            '<graphic xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xlink:href="https://example.org/image2.jpg" />'
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.table_wrap_graphic_tags(xml_file_path)
        # check output
        self.assertEqual(len(result), expected_result_len)
        self.assertEqual(
            ElementTree.tostring(result[0]).decode("utf8"), expected_tag_0_string
        )

    def test_table_wrap_graphic_tags_none(self):
        "test if there are no graphic tags"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        xml_string = "<article />"
        expected = []
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # invoke the function
        result = cleaner.table_wrap_graphic_tags(xml_file_path)
        # check output
        self.assertEqual(result, expected)


class TestTagXlinkHref(unittest.TestCase):
    def test_tag_xlink_href(self):
        xlink_href = "https://example.org/image1.jpg"
        tag = ElementTree.fromstring(
            '<inline-graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="%s" />'
            % xlink_href
        )
        self.assertEqual(cleaner.tag_xlink_href(tag), xlink_href)

    def test_tag_xlink_href_bad_namespace(self):
        "test a tag with an incorrect namespace"
        tag = ElementTree.fromstring(
            '<inline-graphic href="https://example.org/image1.jpg" />'
        )
        self.assertEqual(cleaner.tag_xlink_href(tag), None)

    def test_tag_xlink_href_none(self):
        "test a tag with no xlink:href"
        tag = ElementTree.fromstring("<inline-graphic />")
        self.assertEqual(cleaner.tag_xlink_href(tag), None)


class TestTagXlinkHrefs(unittest.TestCase):
    def test_tag_xlink_hrefs(self):
        xlink_href = "https://example.org/image1.jpg"
        tag1 = ElementTree.fromstring(
            '<inline-graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="%s" />'
            % xlink_href
        )
        tag2 = ElementTree.fromstring(
            '<inline-graphic href="https://example.org/image1.jpg" />'
        )
        tag3 = ElementTree.fromstring("<inline-graphic />")
        tags = [tag1, tag2, tag3]
        self.assertEqual(cleaner.tag_xlink_hrefs(tags), [xlink_href])


class TestChangeInlineGraphicXlinkHrefs(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_change_inline_graphic_xlink_hrefs(self):
        "test modifying the XML for a PRC article"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "30-01-2019-RA-eLife-45644.zip"
        href_to_file_name_map = {"https://example.org/test.jpg": "test.jpg"}
        xml_head = (
            '<?xml version="1.0" encoding="UTF-8" ?>'
            '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and'
            ' Interchange DTD v1.3 20210610//EN"  "JATS-archivearticle1-mathml3.dtd">'
            '<article xmlns:xlink="http://www.w3.org/1999/xlink"'
            ' article-type="research-article" dtd-version="1.3" xml:lang="en">'
        )
        xml_string = (
            "%s"
            '<inline-graphic xlink:href="https://example.org/test.jpg" />'
            "</article>"
        ) % xml_head
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        expected = '%s<inline-graphic xlink:href="test.jpg"/></article>' % xml_head
        # invoke
        cleaner.change_inline_graphic_xlink_hrefs(
            xml_file_path, href_to_file_name_map, identifier
        )
        # check output
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_contents = open_file.read()
        self.assertTrue(('<inline-graphic xlink:href="test.jpg"/>') in xml_contents)
        self.assertEqual(xml_contents, expected)


class TestExternalHrefs(unittest.TestCase):
    def test_tag_xlink_hrefs_external(self):
        external_xlink_href = "https://example.org/image1.jpg"
        href_list = [external_xlink_href, None, "local.jpg"]
        self.assertEqual(cleaner.external_hrefs(href_list), [external_xlink_href])


class TestFilterHrefsByHostname(unittest.TestCase):
    def test_filter_hrefs_by_hostname(self):
        "test filtering approved href values by hostname"
        href_list = [
            "https://i.imgur.com/vc4GR10.Png",
            "https://example.org/image1.jpg",
            None,
            "local.jpg",
            "https://i.imgur.com/vc4GR10.tif",
            (
                "https://cdn.elifesciences.org/public-review-media/"
                "85111/v1/author-response-image-1.jpg"
            ),
        ]
        expected = [
            "https://i.imgur.com/vc4GR10.Png",
            "https://i.imgur.com/vc4GR10.tif",
            (
                "https://cdn.elifesciences.org/public-review-media/"
                "85111/v1/author-response-image-1.jpg"
            ),
        ]
        self.assertEqual(cleaner.filter_hrefs_by_hostname(href_list), expected)


class TestFilterHrefsByFileExtension(unittest.TestCase):
    def test_filter_hrefs_by_file_extension(self):
        "test filtering href values file type"
        href_list = [
            "https://i.imgur.com/vc4GR10.Png",
            "https://example.org/image1.jpg",
            None,
            "local.jpg",
            "https://i.imgur.com/vc4GR10.tif",
        ]
        expected = [
            "https://i.imgur.com/vc4GR10.Png",
            "https://example.org/image1.jpg",
            "local.jpg",
        ]
        self.assertEqual(cleaner.filter_hrefs_by_file_extension(href_list), expected)


class TestApprovedInlineGraphicHrefs(unittest.TestCase):
    def test_approved_inline_graphic_hrefs(self):
        "test filtering approved href values by external domain and file type"
        good_xlink_href = "https://i.imgur.com/vc4GR10.Png"
        href_list = [
            good_xlink_href,
            "https://example.org/image1.jpg",
            None,
            "local.jpg",
            "https://i.imgur.com/vc4GR10.tif",
        ]
        expected = [good_xlink_href]
        self.assertEqual(cleaner.approved_inline_graphic_hrefs(href_list), expected)


class TestTransformEquations(unittest.TestCase):
    "tests for transform_equations()"

    def test_transform_equations(self):
        "test converting inline-graphic tags to disp-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg" />.</p>'
            "<p>Following is a display formula:</p>"
            '<disp-formula id="sa1equ2">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ2.jpg" />'
            "</disp-formula>"
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = cleaner.transform_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)


class TestEquationInlineGraphicHrefs(unittest.TestCase):
    "tests for equation_inline_graphic_hrefs()"

    def test_equation_inline_graphic_hrefs(self):
        "test collecting href values for disp-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = ["elife-inf2.jpg"]
        # invoke
        result = cleaner.equation_inline_graphic_hrefs(sub_article_root, identifier)
        # assert
        self.assertEqual(result, expected)


class TestInlineEquationInlineGraphicHrefs(unittest.TestCase):
    "tests for inline_equation_inline_graphic_hrefs()"

    def test_inline_equation_inline_graphic_hrefs(self):
        "test collecting href values for inline-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = ["elife-inf1.jpg"]
        # invoke
        result = cleaner.inline_equation_inline_graphic_hrefs(
            sub_article_root, identifier
        )
        # assert
        self.assertEqual(result, expected)


class TestTransformInlineEquations(unittest.TestCase):
    "tests for transform_inline_equations()"

    def test_transform_inline_equations(self):
        "test converting inline-graphic tags to inline-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            '<p>First paragraph with an inline equation <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula>.</p>"
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg" /></p>'
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = cleaner.transform_inline_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)


class TestAddFileTagsToXml(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_file_tags_to_xml(self):
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "30-01-2019-RA-eLife-45644.zip"
        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<article-meta>"
            "<files>"
            "<file/>"
            "</files>"
            "</article-meta>"
            "</article>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        file_details_list = [
            {"file_type": "figure", "upload_file_nm": "elife-45644-inf1.png"}
        ]
        # invoke
        cleaner.add_file_tags_to_xml(xml_file_path, file_details_list, identifier)
        # check output
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_contents = open_file.read()
        self.assertTrue(
            (
                '<file file-type="figure">'
                "<upload_file_nm>elife-45644-inf1.png</upload_file_nm>"
                "</file>"
            )
            in xml_contents
        )

    def test_add_file_tags_missing_files_tag(self):
        "test case where the XML does not have a files tag"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "30-01-2019-RA-eLife-45644.zip"
        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<article-meta/>"
            "</article>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        file_details_list = [
            {"file_type": "figure", "upload_file_nm": "elife-45644-inf1.png"}
        ]
        # invoke
        cleaner.add_file_tags_to_xml(xml_file_path, file_details_list, identifier)
        # check output
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_contents = open_file.read()
        self.assertTrue(
            (
                "<files>"
                '<file file-type="figure">'
                "<upload_file_nm>elife-45644-inf1.png</upload_file_nm>"
                "</file>"
                "</files>"
            )
            in xml_contents
        )


class TestAddItemTag(unittest.TestCase):
    "tests for add_item_tag()"

    def test_add_item_tag(self):
        "test adding an item tag to a manifest XML"
        parent = ElementTree.fromstring("<manifest/>")
        file_details = {
            "file_type": "figure",
            "upload_file_nm": "elife-95901-inf1.png",
            "href": "content/elife-95901-inf1.png",
            "id": "inf1",
            "title": "Inline figure 1",
        }
        expected = (
            "<manifest>"
            '<item id="inf1" type="figure">'
            "<title>Inline figure 1</title>"
            '<instance href="content/elife-95901-inf1.png" media-type="image/png" />'
            "</item>"
            "</manifest>"
        )
        # invoke
        cleaner.add_item_tag(parent, file_details)
        # assert
        self.assertEqual(ElementTree.tostring(parent).decode("utf8"), expected)


class TestAddItemTags(unittest.TestCase):
    "tests for add_item_tags()"

    def test_add_item_tags(self):
        "test adding multiple item tags to a manifest XML"
        root = ElementTree.fromstring("<manifest/>")
        file_detail_list = [
            {
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf1.png",
                "href": "content/elife-95901-inf1.png",
                "id": "inf1",
                "title": "Inline figure 1",
            },
            {
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf2.png",
                "href": "content/elife-95901-inf2.png",
                "id": "inf2",
                "title": "Inline figure 2",
            },
        ]
        expected = (
            "<manifest>"
            '<item id="inf1" type="figure">'
            "<title>Inline figure 1</title>"
            '<instance href="content/elife-95901-inf1.png" media-type="image/png" />'
            "</item>"
            '<item id="inf2" type="figure">'
            "<title>Inline figure 2</title>"
            '<instance href="content/elife-95901-inf2.png" media-type="image/png" />'
            "</item>"
            "</manifest>"
        )
        # invoke
        cleaner.add_item_tags(root, file_detail_list)
        # assert
        self.assertEqual(ElementTree.tostring(root).decode("utf8"), expected)


class TestParseManifest(unittest.TestCase):
    "tests for parse_manifest()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_parse_manifest(self):
        "test parsing manifest.xml file"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "10.7554/eLife.95901.1"
        manifest_xml_string = (
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0" />'
        )
        xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            "%s"
        ) % manifest_xml_string
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        # invoke
        result = cleaner.parse_manifest(xml_file_path)
        # assert
        self.assertEqual(
            ElementTree.tostring(result[0]).decode("utf8"), manifest_xml_string
        )
        self.assertEqual(
            result[1],
            {
                "name": "manifest",
                "pubid": None,
                "system": "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd",
            },
        )
        self.assertEqual(result[2], [])


class TestWriteManifestXmlFile(unittest.TestCase):
    "tests for write_manifest_xml_file()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_write_manifest_xml_file(self):
        "test writing manifest XML to disk"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "10.7554/eLife.95901.1"
        doctype_dict = {
            "name": "manifest",
            "pubid": None,
            "system": "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd",
        }
        processing_instructions = []
        manifest_xml_string = (
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0" />'
        )
        root = ElementTree.fromstring(manifest_xml_string)
        xml_file_path = os.path.join(directory.path, xml_file_name)
        expected = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0"/>'
        )
        # invoke
        cleaner.write_manifest_xml_file(
            root, xml_file_path, identifier, doctype_dict, processing_instructions
        )
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
        self.assertEqual(xml_string, expected)


class TestAddItemTagsToManifestXml(unittest.TestCase):
    "tests for add_item_tags_to_manifest_xml()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_item_tags_to_manifest_xml(self):
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "10.7554/eLife.95901.1"
        xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0" />'
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        file_details_list = [
            {
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf1.png",
                "href": "content/elife-95901-inf1.png",
                "id": "inf1",
            }
        ]
        # invoke
        cleaner.add_item_tags_to_manifest_xml(
            xml_file_path, file_details_list, identifier
        )
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            result = open_file.read()
        self.assertTrue(
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
                "<!DOCTYPE manifest SYSTEM"
                ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
                '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
                '<item id="inf1" type="figure">'
                '<instance href="content/elife-95901-inf1.png" media-type="image/png"/>'
                "</item>"
                "</manifest>"
            )
            in result
        )


class TestPrettyManifestXml(unittest.TestCase):
    "tests for pretty_manifest_xml()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_pretty_manifest_xml(self):
        "test formatting manifest XML with new line characters"
        directory = TempDirectory()
        xml_file_name = "test.xml"
        identifier = "10.7554/eLife.95901.1"
        xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item id="inf1" type="figure">'
            '<instance href="content/elife-95901-inf1.png" media-type="image/png"/>'
            "</item>"
            "</manifest>"
        )
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        expected = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">\n'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">\n'
            '<item id="inf1" type="figure">\n'
            '<instance href="content/elife-95901-inf1.png" media-type="image/png"/>\n'
            "</item>\n"
            "</manifest>"
        )
        # invoke
        cleaner.pretty_manifest_xml(xml_file_path, identifier)
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            result = open_file.read()
        self.assertEqual(result, expected)


class TestDocmapUrl(unittest.TestCase):
    def test_docmap_url(self):
        article_id = "1234567890"
        result = cleaner.docmap_url(settings_mock, article_id)
        expected = (
            "https://example.org/path/get-by-manuscript-id?manuscript_id=%s"
            % article_id
        )
        self.assertEqual(result, expected)

    def test_docmap_url_no_settings(self):
        class FakeSettings:
            pass

        article_id = "1234567890"
        result = cleaner.docmap_url(FakeSettings(), article_id)
        expected = None
        self.assertEqual(result, expected)


class TestCleanInlineGraphicTags(unittest.TestCase):
    def test_clean_simple(self):
        "simple test example for clean_inline_graphic_tags"
        xml_string = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>"
            '<ext-link xlink:href="https://example.org/">'
            '<inline-graphic xlink:href="https://example.org/" />'
            "</ext-link>"
            "</p>"
            "</body>"
        )
        root = ElementTree.fromstring(xml_string)
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>"
            '<inline-graphic xlink:href="https://example.org/" />'
            "</p>"
            "</body>"
        )
        cleaner.clean_inline_graphic_tags(root)
        self.assertEqual(ElementTree.tostring(root).decode("utf8"), expected)

    def test_clean_multiple(self):
        "test cleaning multiple inline-graphic tags plus a tag tail value"
        xml_string = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p><bold>A</bold> couple "
            '<ext-link xlink:href="https://example.org/">'
            '<inline-graphic xlink:href="https://example.org/1" /> and '
            "<italic>also</italic> "
            '<inline-graphic xlink:href="https://example.org/2" />'
            "</ext-link> inline graphics."
            '<ext-link xlink:href="https://example.org/another">'
            '<inline-graphic xlink:href="https://example.org/another" />'
            "</ext-link>"
            "</p>"
            "</body>"
        )
        root = ElementTree.fromstring(xml_string)
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p><bold>A</bold> couple "
            '<inline-graphic xlink:href="https://example.org/1" /> and '
            "<italic>also</italic> "
            '<inline-graphic xlink:href="https://example.org/2" />'
            " inline graphics."
            '<inline-graphic xlink:href="https://example.org/another" />'
            "</p>"
            "</body>"
        )
        cleaner.clean_inline_graphic_tags(root)
        self.assertEqual(ElementTree.tostring(root).decode("utf8"), expected)

    def test_clean_no_changes(self):
        "test if the ext-link tag is not a parent of the inline-graphic tag"
        xml_string = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>"
            '<ext-link xlink:href="https://example.org/" />'
            '<inline-graphic xlink:href="https://example.org/" />'
            "</p>"
            "</body>"
        )
        root = ElementTree.fromstring(xml_string)
        expected = xml_string
        cleaner.clean_inline_graphic_tags(root)
        self.assertEqual(ElementTree.tostring(root).decode("utf8"), expected)


class TestGetDocmap(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url = "https://example.org/"

    @patch("requests.get")
    def test_get_docmap_200(self, mock_requests_get):
        content = b"test"
        status_code = 200
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = cleaner.get_docmap(self.url)
        self.assertEqual(result, content)

    @patch("requests.get")
    def test_get_docmap_404(self, mock_requests_get):
        status_code = 404
        mock_requests_get.return_value = FakeResponse(status_code)
        with self.assertRaises(Exception):
            cleaner.get_docmap(self.url)


class TestGetDocmapByAccountId(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url = "https://example.org/"

    @patch("requests.get")
    def test_get_docmap_by_account_id_blank(self, mock_requests_get):
        "test for non-list JSON returned"
        content = b""
        status_code = 200
        expected = None
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = cleaner.get_docmap_by_account_id(
            self.url, settings_mock.docmap_account_id
        )
        self.assertEqual(result, expected)

    @patch("requests.get")
    def test_get_docmap_by_account_id_empty(self, mock_requests_get):
        "test for non-list JSON returned"
        content = b"{}"
        status_code = 200
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = cleaner.get_docmap_by_account_id(
            self.url, settings_mock.docmap_account_id
        )
        self.assertEqual(result, content)

    @patch("requests.get")
    def test_get_docmap_by_account_id_list_content(self, mock_requests_get):
        "test for when a list of values is returned"
        elife_docmap = {
            "publisher": {"account": {"id": "https://sciety.org/groups/elife"}}
        }
        non_elife_docmap = {"publisher": {"account": {"id": "https://example.org"}}}
        content = b"[%s, %s]" % (
            json.dumps(non_elife_docmap).encode("utf-8"),
            json.dumps(elife_docmap).encode("utf-8"),
        )
        status_code = 200
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = cleaner.get_docmap_by_account_id(
            self.url, settings_mock.docmap_account_id
        )
        self.assertEqual(result, json.dumps(elife_docmap))


class TestGetDocmapString(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url = "https://example.org/"

    @patch("requests.get")
    def test_get_docmap_string(self, mock_requests_get):
        "test for non-list JSON returned"
        article_id = 84364
        identifier = "elife-preprint-84364-v2.xml"
        caller_name = "ScheduleCrossrefPreprint"
        content = b'{"foo": "bar"}'
        status_code = 200
        expected = content
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        # invoke
        result = cleaner.get_docmap_string(
            settings_mock, article_id, identifier, caller_name, self.logger
        )
        # assert
        self.assertEqual(result, expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            "%s, getting docmap_string for identifier: %s" % (caller_name, identifier),
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "%s, docmap_endpoint_url: %spath/get-by-manuscript-id?manuscript_id=%s"
            % (caller_name, self.url, article_id),
        )


class TestGetDocmapStringWithRetry(unittest.TestCase):
    "tests for cleaner.get_docmap_string_with_retry()"

    def setUp(self):
        self.logger = FakeLogger()
        # set constants for faster testing
        self.retry = 2
        self.original_constants = {
            "DOCMAP_SLEEP_SECONDS": cleaner.DOCMAP_SLEEP_SECONDS,
            "DOCMAP_RETRY": cleaner.DOCMAP_RETRY,
        }
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = self.retry

    def tearDown(self):
        # reset constants
        for key, value in self.original_constants.items():
            setattr(cleaner, key, value)

    @patch.object(cleaner, "get_docmap_string")
    def test_get_get_docmap_string_with_retry(
        self,
        fake_get_docmap_string,
    ):
        "test if an exception is raised when generating an article"
        article_id = "84364"
        caller_name = "ScheduleCrossrefPreprint"
        docmap_string = "docmap"
        fake_get_docmap_string.return_value = docmap_string
        # invoke
        result = cleaner.get_docmap_string_with_retry(
            settings_mock, article_id, caller_name, self.logger
        )
        # check assertions
        self.assertEqual(result, docmap_string)
        self.assertEqual(
            self.logger.loginfo[-1],
            ("%s, try number 0 to get docmap_string for article_id %s")
            % (caller_name, article_id),
        )

    @patch.object(cleaner, "get_docmap_string")
    def test_get_docmap_exception(
        self,
        fake_get_docmap_string,
    ):
        "test if an exception is raised when getting docmap"
        article_id = "84364"
        caller_name = "ScheduleCrossrefPreprint"
        fake_get_docmap_string.side_effect = Exception("An exception")
        # invoke
        with self.assertRaises(RuntimeError):
            cleaner.get_docmap_string_with_retry(
                settings_mock, article_id, caller_name, self.logger
            )
        # check assertions
        self.assertEqual(
            self.logger.loginfo[-1],
            ("%s, exceeded %s retries to get docmap_string for article_id %s")
            % (caller_name, self.retry, article_id),
        )


class TestPublishedDateFromHistory(unittest.TestCase):
    "tests for published_date_from_history()"

    def test_published_date_from_history(self):
        "test finding first version pub date from history data"
        history_data = [
            {"doi": "preprint_server_doi", "published": "2024-01-01"},
            {"doi": "10.7554/eLife.95901.1", "published": "2024-01-02"},
            {"doi": "10.7554/eLife.95901.2", "published": "2024-01-03"},
        ]
        doi = "10.7554/eLife.95901"
        expected = time.strptime("2024-01-02 +0000", "%Y-%m-%d %z")
        # invoke
        result = cleaner.published_date_from_history(history_data, doi)
        # assert
        self.assertEqual(result, expected)

    def test_no_history_data(self):
        "test if there is no history data"
        history_data = []
        doi = "10.7554/eLife.95901"
        expected = None
        # invoke
        result = cleaner.published_date_from_history(history_data, doi)
        # assert
        self.assertEqual(result, expected)


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
            "2023-03-20 16:36:08,542 WARNING elifecleaner:activity_AcceptedSubmissionPeerReviewImages:do_activity: https://example.org/fake.jpg peer review image href was not approved for downloading\n"
            "2023-04-21 17:10:15,942 WARNING elifecleaner:activity_AcceptedSubmissionVersionDoi:do_activity: 22-02-2022-CR-eLife-78088.zip A version DOI was not added to the XML\n"
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
            "https://example.org/fake.jpg peer review image href was not approved for downloading",
            "22-02-2022-CR-eLife-78088.zip A version DOI was not added to the XML",
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
            "https://example.org/fake.jpg peer review image href was not approved for downloading",
        ]

        comments = cleaner.production_comments_for_xml(self.cleaner_log)
        self.assertEqual(comments, expected)


class TestModifyVolume(unittest.TestCase):
    "tests for modify_volume()"

    def test_modify_volume(self):
        "test setting existing volume tag value"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume></volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        volume = 13
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume>13</volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_volume(xml_root, volume)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_add_volume_tag(self):
        "test adding a volume tag"
        xml_root = ElementTree.fromstring(
            "<article><front><article-meta /></front></article>"
        )
        volume = 13
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume>13</volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_volume(xml_root, volume)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_no_volume(self):
        "test no volume will remove the tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume>1</volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        volume = None
        expected = "<article><front><article-meta /></front></article>"
        # invoke
        cleaner.modify_volume(xml_root, volume)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyArticleCategories(unittest.TestCase):
    "tests for modify_article_categories()"

    def test_modify_article_categories(self):
        "test removing and adding subject tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="heading">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        display_channel = "Research Article"
        article_categories = ["Epidemiology and Global Health"]
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="display-channel">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            '<subj-group subj-group-type="heading">'
            "<subject>Epidemiology and Global Health</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_article_categories(xml_root, display_channel, article_categories)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_add_article_categories(self):
        "test adding article-categories tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            '<article-id pub-id-type="doi" specific-use="version">'
            "10.7554/eLife.95901.1"
            "</article-id>"
            "<title-group>"
            "<article-title>Title</article-title>"
            "</title-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        display_channel = "Research Article"
        article_categories = ["Epidemiology and Global Health"]
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            '<article-id pub-id-type="doi" specific-use="version">'
            "10.7554/eLife.95901.1"
            "</article-id>"
            "<article-categories>"
            '<subj-group subj-group-type="display-channel">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            '<subj-group subj-group-type="heading">'
            "<subject>Epidemiology and Global Health</subject>"
            "</subj-group>"
            "</article-categories>"
            "<title-group>"
            "<article-title>Title</article-title>"
            "</title-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_article_categories(xml_root, display_channel, article_categories)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_no_article_categories(self):
        "test no data will remove the article-categories tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="heading">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = "<article><front><article-meta /></front></article>"
        # invoke
        cleaner.modify_article_categories(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyPermissions(unittest.TestCase):
    "tests for modify_permissions()"

    def setUp(self):
        directory = TempDirectory()
        # extract XML from the MECA zip file
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        zip_xml_file_path = "content/24301711.xml"
        with zipfile.ZipFile(meca_file_path, "r") as open_zipfile:
            open_zipfile.extract(zip_xml_file_path, directory.path)
            self.xml_file_path = os.path.join(directory.path, zip_xml_file_path)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_modify_permissions(self):
        "test removing permissions and adding license and copyright"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<permissions>"
            "<copyright-year>2073</copyright-year>"
            "</permissions>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        license_data_dict = OrderedDict(
            [
                ("license_id", 1),
                ("license_type", "open-access"),
                ("copyright", True),
                ("href", "https://creativecommons.org/licenses/by/4.0/"),
                ("name", "Creative Commons Attribution License"),
                ("paragraph1", "This article is distributed under the terms of the "),
                (
                    "paragraph2",
                    (
                        ", which permits unrestricted use and redistribution provided that the"
                        " original author and source are credited."
                    ),
                ),
            ]
        )
        copyright_year = "2024"
        copyright_holder = "Liang et al"
        expected = (
            '<article xmlns:ali="http://www.niso.org/schemas/ali/1.0/"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<permissions>"
            "<copyright-statement>© 2024, Liang et al</copyright-statement>"
            "<copyright-year>2024</copyright-year>"
            "<copyright-holder>Liang et al</copyright-holder>"
            "<ali:free_to_read />"
            '<license xlink:href="https://creativecommons.org/licenses/by/4.0/">'
            "<ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref>"
            "<license-p>This article is distributed under the terms of the"
            ' <ext-link ext-link-type="uri"'
            ' xlink:href="https://creativecommons.org/licenses/by/4.0/">'
            "Creative Commons Attribution License"
            "</ext-link>"
            ", which permits unrestricted use and redistribution provided that the"
            " original author and source are credited."
            "</license-p>"
            "</license>"
            "</permissions>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_permissions(
            xml_root, license_data_dict, copyright_year, copyright_holder
        )
        # assert
        xml_string = ElementTree.tostring(xml_root, encoding="utf-8").decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_add_permissions_tag(self):
        "test adding permissions tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<history />"
            "<pub-history />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        license_data_dict = OrderedDict(
            [
                ("license_id", 2),
                ("license_type", "open-access"),
                ("copyright", False),
                ("href", "https://creativecommons.org/publicdomain/zero/1.0/"),
                ("name", "Creative Commons CC0 public domain dedication"),
                (
                    "paragraph1",
                    (
                        "This is an open-access article, free of all copyright, and may be"
                        " freely reproduced, distributed, transmitted, modified, built upon,"
                        " or otherwise used by anyone for any lawful purpose."
                        " The work is made available under the "
                    ),
                ),
                ("paragraph2", "."),
            ]
        )
        copyright_year = "2024"
        copyright_holder = "Liang et al"
        expected = (
            '<article xmlns:ali="http://www.niso.org/schemas/ali/1.0/"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<history />"
            "<pub-history />"
            "<permissions>"
            "<ali:free_to_read />"
            '<license xlink:href="https://creativecommons.org/publicdomain/zero/1.0/">'
            "<ali:license_ref>https://creativecommons.org/publicdomain/zero/1.0/</ali:license_ref>"
            "<license-p>This is an open-access article, free of all copyright,"
            " and may be freely reproduced, distributed, transmitted, modified,"
            " built upon, or otherwise used by anyone for any lawful purpose."
            " The work is made available under the"
            ' <ext-link ext-link-type="uri"'
            ' xlink:href="https://creativecommons.org/publicdomain/zero/1.0/">'
            "Creative Commons CC0 public domain dedication"
            "</ext-link>"
            "."
            "</license-p>"
            "</license>"
            "</permissions>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        cleaner.modify_permissions(
            xml_root, license_data_dict, copyright_year, copyright_holder
        )
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestSetDataAvailability(unittest.TestCase):
    "tests for set_data_availability()"

    def test_set_data_availability(self):
        "test adding data availability sec XML"
        xml_root = ElementTree.fromstring(
            '<article><back><sec id="s1"/></back></article>'
        )
        data_availability_statement = "Statement."
        expected = (
            "<article>"
            "<back>"
            '<sec id="das" sec-type="data-availability">'
            "<p>Statement.</p>"
            "</sec>"
            '<sec id="s1" />'
            "</back>"
            "</article>"
        )
        # invoke
        cleaner.set_data_availability(xml_root, data_availability_statement)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestSetDataAvailabilityContent(unittest.TestCase):
    "tests for set_data_availability_content()"

    def test_set_data_availability_content(self):
        "test adding content to a p tag in a data availability statement"
        parent = ElementTree.fromstring("<back/>")
        data_availability_statement = "<italic>A</italic> statement & more."
        expected = "<back><p><italic>A</italic> statement &amp; more.</p></back>"
        # invoke
        cleaner.set_data_availability_content(parent, data_availability_statement)
        # assert
        xml_string = ElementTree.tostring(parent).decode("utf-8")
        self.assertEqual(xml_string, expected)


EXAMPLE_DATA_CITATIONS = [
    {
        "specific_use": "generated",
        "authors_text_list": (
            "Touray AO, Rajesh R, Isebe I, Sternlieb T, Loock M, Kutova O, Cestari I"
        ),
        "id": "https://dataview.ncbi.nlm.nih.gov/object/PRJNA934938",
        "license_info": "SRA Bioproject PRJNA934938",
        "title": "Trypanosoma brucei brucei strain:Lister 427 DNA or RNA sequencing",
        "year": "2023",
    },
    {
        "specific_use": "analyzed",
        "authors_text_list": "K Kok, A Ay, L Li",
        "id": "https://doi.org/10.5061/dryad.cv323",
        "license_info": "Dryad Digital Repository",
        "title": "Genome-wide errant targeting by Hairy",
        "year": "2015",
    },
]


class TestSetDataCitation(unittest.TestCase):
    "tests for set_data_citation()"

    def test_set_data_citation(self):
        "test adding element-citation tag to ref tag"
        parent = ElementTree.fromstring("<ref/>")
        dataset = Dataset()
        # set both uri and doi values for test coverage
        dataset.uri = "https://example.org/"
        dataset.doi = "https://doi.org/example"
        dataset.add_author("X Author")
        dataset.year = "2025"
        dataset.title = "Sample Data"
        dataset.license_info = "Dryad Digital Repository"
        specific_use = "generated"
        expected = (
            "<ref>"
            '<element-citation publication-type="data" specific-use="generated">'
            '<person-group person-group-type="author">'
            "<collab>X Author</collab>"
            "</person-group>"
            "<article-title>Sample Data</article-title>"
            "<source>Dryad Digital Repository</source>"
            '<year iso-8601-date="2025">2025</year>'
            '<ext-link ext-link-type="uri" xlink:href="https://example.org/" />'
            '<pub-id pub-id-type="doi">https://doi.org/example</pub-id>'
            "</element-citation>"
            "</ref>"
        )
        # invoke
        cleaner.set_data_citation(parent, dataset, specific_use)
        # assert
        xml_string = ElementTree.tostring(parent).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestSetDataCitations(unittest.TestCase):
    "tests for set_data_citations()"

    def test_set_data_citations(self):
        "test adding ref and element-citation tags for data citations to a ref-list"
        xml_root = ElementTree.fromstring("<article><back><ref-list/></back></article>")
        data_citations = EXAMPLE_DATA_CITATIONS
        dataset_list = cleaner.data_citation_dataset_list(data_citations)
        expected = (
            "<article>"
            "<back>"
            "<ref-list>"
            '<ref id="dataref1">'
            '<element-citation publication-type="data" specific-use="generated">'
            '<person-group person-group-type="author">'
            "<collab>Touray AO, Rajesh R, Isebe I, Sternlieb T,"
            " Loock M, Kutova O, Cestari I</collab>"
            "</person-group>"
            "<article-title>Trypanosoma brucei brucei strain:Lister 427 DNA or"
            " RNA sequencing</article-title>"
            "<source>SRA Bioproject PRJNA934938</source>"
            '<year iso-8601-date="2023">2023</year>'
            '<ext-link ext-link-type="uri"'
            ' xlink:href="https://dataview.ncbi.nlm.nih.gov/object/PRJNA934938" />'
            "</element-citation>"
            "</ref>"
            '<ref id="dataref2">'
            '<element-citation publication-type="data" specific-use="analyzed">'
            '<person-group person-group-type="author">'
            "<collab>K Kok, A Ay, L Li</collab>"
            "</person-group>"
            "<article-title>Genome-wide errant targeting by Hairy</article-title>"
            "<source>Dryad Digital Repository</source>"
            '<year iso-8601-date="2015">2015</year>'
            '<pub-id pub-id-type="doi">10.5061/dryad.cv323</pub-id>'
            "</element-citation>"
            "</ref>"
            "</ref-list>"
            "</back>"
            "</article>"
        )
        # invoke
        cleaner.set_data_citations(xml_root, dataset_list)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_no_ref_list_tag(self):
        "test if there is no ref-list tag in the XML"
        xml_string = "<article><back /></article>"
        xml_root = ElementTree.fromstring(xml_string)
        data_citations = EXAMPLE_DATA_CITATIONS
        dataset_list = cleaner.data_citation_dataset_list(data_citations)
        expected = xml_string
        # invoke
        cleaner.set_data_citations(xml_root, dataset_list)
        # assert
        modified_xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(modified_xml_string, expected)
