import unittest
import os
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
from elifecleaner.transform import ArticleZipFile
from provider import meca
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeSession


class TestMecaFileName(unittest.TestCase):
    "tests for meca_file_name()"

    def test_meca_file_name(self):
        article_id = 95901
        version = "1"
        expected = "95901-v1-meca.zip"
        result = meca.meca_file_name(article_id, version)
        self.assertEqual(result, expected)


class TestMecaContentFolder(unittest.TestCase):
    "tests for meca_content_folder()"

    def test_meca_content_folder(self):
        "test getting subfolder name"
        article_xml_path = "content/24301711.xml"
        expected = "content"
        self.assertEqual(meca.meca_content_folder(article_xml_path), expected)

    def test_multiple_folders(self):
        "test if there are multiple folder names"
        article_xml_path = "folder_1/folder_2/24301711.xml"
        expected = "folder_1/folder_2"
        self.assertEqual(meca.meca_content_folder(article_xml_path), expected)

    def test_none(self):
        "test if article_xml_path is None"
        article_xml_path = None
        expected = None
        self.assertEqual(meca.meca_content_folder(article_xml_path), expected)


def manifest_xml_string_snippet(
    article_xml_path="content/24301711.xml",
    article_pdf_path="content/elife-preprint-95901-v1.pdf",
):
    "fixture XML for testing"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        "<!DOCTYPE manifest SYSTEM"
        ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
        '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
        '<item type="article" id="elife-95901-v1">'
        '<instance media-type="application/xml" href="%s"/>'
        '<instance media-type="application/pdf" href="%s"/>'
        "</item>"
        "</manifest>" % (article_xml_path, article_pdf_path)
    )


class TestGetMecaArticleXmlPath(unittest.TestCase):
    "tests for get_meca_article_xml_path()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_meca_article_xml_path(self):
        "test getting the article XML path from a manifest.xml"
        directory = TempDirectory()
        article_xml_path = "content/24301711.xml"
        manifest_xml_string = manifest_xml_string_snippet(
            article_xml_path=article_xml_path
        )
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        logger = FakeLogger()
        result = meca.get_meca_article_xml_path(
            directory.path, version_doi, caller_name, logger
        )
        self.assertEqual(result, article_xml_path)

    def test_no_manifest(self):
        "test if there is no manifest.xml file"
        directory = TempDirectory()
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        logger = FakeLogger()
        result = meca.get_meca_article_xml_path(
            directory.path, version_doi, caller_name, logger
        )
        self.assertEqual(result, None)
        self.assertEqual(
            logger.logexception,
            ("%s, manifest_file_path %s/manifest.xml not found for version DOI %s")
            % (caller_name, directory.path, version_doi),
        )


class TestGetMecaArticlePdfPath(unittest.TestCase):
    "tests for get_meca_article_pdf_path()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_get_meca_article_pdf_path(self):
        "test getting the article XML path from a manifest.xml"
        directory = TempDirectory()
        article_pdf_path = "content/elife-preprint-95901-v1.pdf"
        manifest_xml_string = manifest_xml_string_snippet(
            article_pdf_path=article_pdf_path
        )
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        logger = FakeLogger()
        result = meca.get_meca_article_pdf_path(
            directory.path, version_doi, caller_name, logger
        )
        self.assertEqual(result, article_pdf_path)

    def test_no_manifest(self):
        "test if there is no manifest.xml file"
        directory = TempDirectory()
        caller_name = "test"
        version_doi = "10.7554/eLife.95901.1"
        logger = FakeLogger()
        result = meca.get_meca_article_pdf_path(
            directory.path, version_doi, caller_name, logger
        )
        self.assertEqual(result, None)
        self.assertEqual(
            logger.logexception,
            ("%s, manifest_file_path %s/manifest.xml not found for version DOI %s")
            % (caller_name, directory.path, version_doi),
        )


class TestPostXmlFile(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        start_xml = b"<root/>"
        self.transformed_xml = b"<root>Modified.</root>"
        self.file_path = os.path.join(self.directory.path, "file.xml")
        with open(self.file_path, "wb") as open_file:
            open_file.write(start_xml)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.post")
    def test_post_xml_file(self, fake_post):
        "test post_xml_file()"
        status_code = 200
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        result = meca.post_xml_file(
            self.file_path,
            settings_mock.meca_dtd_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, self.transformed_xml)

    @patch("requests.post")
    def test_status_code_400(self, fake_post):
        "test response status_code 400"
        status_code = 400
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        with self.assertRaises(Exception):
            meca.post_xml_file(
                self.file_path,
                settings_mock.meca_xsl_endpoint,
                settings_mock.user_agent,
                "test",
                logger,
            )

    @patch("requests.post")
    def test_bad_response(self, fake_post):
        "test if response content is None"
        logger = FakeLogger()
        fake_post.return_value = None
        result = meca.post_xml_file(
            self.file_path,
            settings_mock.meca_xsl_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, None)


class TesetPostToEndpoint(unittest.TestCase):
    "tests for post_to_endpoint()"

    def setUp(self):
        self.xml_file_path = "article.xml"
        self.endpoint_url = settings_mock.meca_dtd_endpoint
        self.caller_name = "ValidateJatsDtd"

    @patch.object(meca, "post_xml_file")
    def test_post_to_endpoint(self, fake_post_xml_file):
        "test normal response content returned"
        logger = FakeLogger()
        response_content = b""
        fake_post_xml_file.return_value = response_content
        # invoke
        result = meca.post_to_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        # assert
        self.assertEqual(result, response_content)

    @patch.object(meca, "post_xml_file")
    def test_exception(self, fake_post_xml_file):
        "test exception raised"
        logger = FakeLogger()
        fake_post_xml_file.side_effect = Exception("An exception")
        # invoke
        result = meca.post_to_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        # assert
        self.assertEqual(result, None)
        self.assertEqual(
            logger.logexception,
            "%s, posting %s to endpoint %s: An exception"
            % (self.caller_name, self.xml_file_path, self.endpoint_url),
        )


class TestPostFileDataToEndpoint(unittest.TestCase):
    "tests for post_file_data_to_endpoint()"

    def setUp(self):
        self.directory = TempDirectory()
        start_xml = b"<root/>"
        self.transformed_xml = b"<root>Modified.</root>"
        self.file_path = os.path.join(self.directory.path, "file.xml")
        with open(self.file_path, "wb") as open_file:
            open_file.write(start_xml)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.post")
    def test_post_data(self, fake_post):
        "test post_file_data_to_endpoint()"
        status_code = 200
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        result = meca.post_file_data_to_endpoint(
            self.file_path,
            settings_mock.meca_dtd_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, self.transformed_xml)

    @patch("requests.post")
    def test_status_code_400(self, fake_post):
        "test response status_code 400"
        status_code = 400
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        with self.assertRaises(Exception):
            meca.post_file_data_to_endpoint(
                self.file_path,
                settings_mock.meca_xsl_endpoint,
                settings_mock.user_agent,
                "test",
                logger,
            )

    @patch("requests.post")
    def test_bad_response(self, fake_post):
        "test if response content is None"
        logger = FakeLogger()
        fake_post.return_value = None
        result = meca.post_file_data_to_endpoint(
            self.file_path,
            settings_mock.meca_xsl_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, None)


class TesetPostToPreprintPdfEndpoint(unittest.TestCase):
    "tests for post_to_preprint_pdf_endpoint()"

    def setUp(self):
        self.xml_file_path = "article.xml"
        self.endpoint_url = settings_mock.meca_dtd_endpoint
        self.caller_name = "GeneratePreprintPDF"

    @patch.object(meca, "post_file_data_to_endpoint")
    def test_post(self, fake_post_file_data):
        "test normal response content returned"
        logger = FakeLogger()
        response_content = b""
        fake_post_file_data.return_value = response_content
        # invoke
        result = meca.post_to_preprint_pdf_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        # assert
        self.assertEqual(result, response_content)

    @patch.object(meca, "post_file_data_to_endpoint")
    def test_exception(self, fake_post_file_data):
        "test exception raised"
        logger = FakeLogger()
        fake_post_file_data.side_effect = Exception("An exception")
        # invoke
        result = meca.post_to_preprint_pdf_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        # assert
        self.assertEqual(result, None)
        self.assertEqual(
            logger.logexception,
            "%s, posting %s to preprint PDF endpoint %s: An exception"
            % (self.caller_name, self.xml_file_path, self.endpoint_url),
        )


class TestLogToSession(unittest.TestCase):
    "tests for log_to_session()"

    def test_add_log_messages(self):
        "test adding new log_messages key to the session"
        mock_session = FakeSession({})
        log_message = "A log message"
        # invoke
        meca.log_to_session(log_message, mock_session)
        # assert
        self.assertEqual(mock_session.get_value("log_messages"), log_message)

    def test_append_log_messages(self):
        "test appending a log_message to existing log_messages in the session"
        log_messages = "First log message."
        mock_session = FakeSession({"log_messages": log_messages})
        log_message = "A log message"
        # invoke
        meca.log_to_session(log_message, mock_session)
        # assert
        self.assertEqual(
            mock_session.get_value("log_messages"), "%s%s" % (log_messages, log_message)
        )


class TestCollectTransformationFileDetails(unittest.TestCase):
    "tests for collect_transformation_file_details()"

    def test_collect_transformation_file_details(self):
        "test collecting data from the XML for a variant"
        variant_data = {
            "parent_tag_name": "fig",
            "graphic_tag_name": "graphic",
            "file_type": "figure",
        }
        root = ElementTree.fromstring(
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<sub-article id="sa1">\n'
            "<body>\n"
            "<p>First paragraph.</p>\n"
            '<fig id="sa1fig1">\n'
            "<label>Review image 1.</label>\n"
            "<caption>\n"
            "<title>Caption title.</title>\n"
            "<p>Caption paragraph.</p>\n"
            "</caption>\n"
            '<graphic mimetype="image" mime-subtype="jpg"'
            ' xlink:href="elife-95901-sa1-fig1.jpg"/>\n'
            "</fig>\n"
            "</body>\n"
            "</sub-article>\n"
            "</article>"
        )
        file_transformations = [
            (
                ArticleZipFile("elife-95901-inf1.jpg", "None", "None"),
                ArticleZipFile("elife-95901-sa1-fig1.jpg", "None", "None"),
            ),
        ]
        content_subfolder = "subfolder"
        expected = [
            {
                "file_type": "figure",
                "from_href": "subfolder/elife-95901-inf1.jpg",
                "href": "subfolder/elife-95901-sa1-fig1.jpg",
                "id": "sa1fig1",
                "title": "Review image 1.",
            }
        ]
        # invoke
        result = meca.collect_transformation_file_details(
            variant_data, root, file_transformations, content_subfolder
        )
        # assert
        self.assertEqual(result, expected)


class TestRewriteItemTags(unittest.TestCase):
    "tests for rewrite_item_tags()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_rewrite_item_tags(self):
        "test rewriting item tag XML in a manifest.xml"
        directory = TempDirectory()
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        manifest_xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item type="figure">'
            '<instance href="content/local.jpg"/>'
            "</item>"
            "</manifest>"
        )
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        file_detail_list = [
            {
                "file_type": "figure",
                "from_href": "content/local.jpg",
                "href": "content/sa1-fig1.jpg",
                "id": "sa1fig1",
                "title": "Review image 1.",
            },
            {
                "file_type": "figure",
                "from_href": "content/local2.jpg",
                "href": "content/sa2-fig1.jpg",
                "id": "sa2fig1",
                "title": "Review image 1.",
            },
        ]
        version_doi = "10.7554/eLife.95901.1"
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        meca.rewrite_item_tags(
            manifest_xml_path, file_detail_list, version_doi, caller_name, logger
        )
        # assert
        result_xml_string = ""
        with open(manifest_xml_path, "r", encoding="utf-8") as open_file:
            result_xml_string = open_file.read()
        self.assertTrue(
            (
                '<item id="sa1fig1" type="figure">'
                "<title>Review image 1.</title>"
                '<instance href="content/sa1-fig1.jpg" media-type="image/jpeg"/>'
                "</item>"
            )
            in result_xml_string
        )

    def test_removing_item_tags(self):
        "test when the file detail mising a href implies the item tag should be removed"
        directory = TempDirectory()
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        manifest_xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item type="figure">'
            '<instance href="content/local.jpg"/>'
            "</item>"
            "</manifest>"
        )
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        file_detail_list = [
            {
                "file_type": "figure",
                "from_href": "content/local.jpg",
                "href": None,
                "id": "sa1fig1",
                "title": "Review image 1.",
            },
        ]
        version_doi = "10.7554/eLife.95901.1"
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        meca.rewrite_item_tags(
            manifest_xml_path, file_detail_list, version_doi, caller_name, logger
        )
        # assert
        result_xml_string = ""
        with open(manifest_xml_path, "r", encoding="utf-8") as open_file:
            result_xml_string = open_file.read()
        self.assertTrue(
            (
                '<item id="sa1fig1" type="figure">'
                "<title>Review image 1.</title>"
                '<instance href="content/sa1-fig1.jpg" media-type="image/jpeg"/>'
                "</item>"
            )
            not in result_xml_string
        )

    def test_multiple_instance_tags(self):
        "test rewriting item tag XML in a manifest.xml which has multiple instance tags"
        directory = TempDirectory()
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        manifest_xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item type="article">'
            '<instance media-type="application/xml" href="content/local.xml"/>'
            '<instance media-type="application/pdf" href="content/local.pdf"/>'
            "</item>"
            "</manifest>"
        )
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        file_detail_list = [
            {
                "file_type": "article",
                "from_href": "content/local.pdf",
                "href": "content/new.pdf",
                "id": None,
                "title": None,
            },
        ]
        version_doi = "10.7554/eLife.95901.1"
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        meca.rewrite_item_tags(
            manifest_xml_path, file_detail_list, version_doi, caller_name, logger
        )
        # assert
        result_xml_string = ""
        with open(manifest_xml_path, "r", encoding="utf-8") as open_file:
            result_xml_string = open_file.read()
        self.assertTrue(
            (
                '<item type="article">'
                '<instance media-type="application/xml" href="content/local.xml"/>'
                '<instance href="content/new.pdf" media-type="application/pdf"/>'
                "</item>"
            )
            in result_xml_string
        )


class TestAddInstanceTags(unittest.TestCase):
    "tests for add_instance_tags()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_instance_tags(self):
        "test adding instance tag to item tag XML in a manifest.xml"
        directory = TempDirectory()
        manifest_xml_path = os.path.join(directory.path, "manifest.xml")
        manifest_xml_string = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            "<!DOCTYPE manifest SYSTEM"
            ' "http://schema.highwire.org/public/MECA/v0.9/Manifest/Manifest.dtd">'
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item type="article">'
            '<instance media-type="application/xml" href="content/local.xml"/>'
            "</item>"
            "</manifest>"
        )
        with open(manifest_xml_path, "w", encoding="utf-8") as open_file:
            open_file.write(manifest_xml_string)
        file_detail_list = [
            {
                "file_type": "article",
                "from_href": "content/local.jpg",
                "href": "content/local.pdf",
                "id": None,
                "title": None,
            },
        ]
        version_doi = "10.7554/eLife.95901.1"
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        meca.add_instance_tags(
            manifest_xml_path, file_detail_list, version_doi, caller_name, logger
        )
        # assert
        result_xml_string = ""
        with open(manifest_xml_path, "r", encoding="utf-8") as open_file:
            result_xml_string = open_file.read()
        self.assertTrue(
            (
                '<item type="article">'
                '<instance media-type="application/xml" href="content/local.xml"/>'
                '<instance href="content/local.pdf" media-type="application/pdf"/>'
                "</item>"
            )
            in result_xml_string
        )


class TestTransferXml(unittest.TestCase):
    "tests for transfer_xml()"

    def test_transfer_xml(self):
        "simple test of transfer_xml"
        self.assertTrue(isinstance(meca.transfer_xml(), str))
