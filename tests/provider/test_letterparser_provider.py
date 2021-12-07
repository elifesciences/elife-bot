# coding=utf-8

import os
import unittest
import zipfile
import docker
from mock import patch
from testfixtures import TempDirectory
from elifearticle.article import Article
import tests.settings_mock as settings_mock
import provider.letterparser_provider as letterparser_provider


class TestLetterParserProvider(unittest.TestCase):
    def setUp(self):
        self.file_name = "tests/fixtures/letterparser/sections.docx"
        self.blank_config = {}

    def test_letterparser_config(self):
        """test reading the letterparser config file"""
        config = letterparser_provider.letterparser_config(settings_mock)
        self.assertEqual(config.get("docker_image"), "elifesciences/pandoc:2.9.1.1")

    def test_parse_file(self):
        """test parsing docx file with pandoc which may be called via Docker"""
        # blank config will use pandoc executable if present, otherwise via Docker image default
        expected = (
            "<p><bold>Preamble\n"
            "</bold></p>\n"
            "<p>Preamble ....</p>\n"
            "<p><bold>Decision letter</bold></p>\n"
            "<p>Decision letter ....</p>\n"
            "<p><bold>Author response</bold></p>\n"
            "<p>Author response ....</p>\n"
        )

        output = letterparser_provider.parse_file(self.file_name, self.blank_config)
        self.assertEqual(
            output, expected, "Docker pandoc output not equal, is Docker running?"
        )

    @patch("letterparser.parse.parse_file")
    def test_parse_file_docker_exception(self, fake_letterparser_parse):
        fake_letterparser_parse.side_effect = docker.errors.APIError("Fake exception")
        with self.assertRaises(docker.errors.APIError):
            letterparser_provider.parse_file(self.file_name, self.blank_config)

    @patch("letterparser.parse.parse_file")
    def test_parse_file_other_exception(self, fake_letterparser_parse):
        fake_letterparser_parse.side_effect = Exception("Other fake exception")
        with self.assertRaises(Exception):
            letterparser_provider.parse_file(self.file_name, self.blank_config)


class TestValidateArticles(unittest.TestCase):
    def test_validate_articles_valid(self):
        """test two articles that are completely valid"""
        articles = [
            Article(
                "10.7554/eLife.99999.sa1",
                "Decision letter: Test",
            ),
            Article(
                "10.7554/eLife.99999.sa2",
                "Author response: Test",
            ),
        ]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertTrue(valid)
        self.assertTrue(len(error_messages) == 0)

    def test_validate_articles_empty(self):
        """test empty article list"""
        articles = []
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertFalse(valid)
        self.assertTrue(len(error_messages) > 0)

    def test_validate_articles_count(self):
        """test one article which is enough"""
        articles = [Article("10.7554/eLife.99999.sa1")]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertTrue(valid)
        self.assertTrue(len(error_messages) == 0)

    def test_validate_articles_doi(self):
        """test article missing a DOI"""
        articles = [Article(), Article()]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertFalse(valid)
        self.assertTrue(len(error_messages) > 0)

    def test_validate_articles_no_titles(self):
        """test two articles without titles"""
        articles = [
            Article("10.7554/eLife.99999.sa1"),
            Article("10.7554/eLife.99999.sa2"),
        ]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertTrue(valid)
        self.assertTrue(len(error_messages) == 0)


class TestCheckInput(unittest.TestCase):
    def setUp(self):
        self.temp_directory = TempDirectory()

    def tearDown(self):
        TempDirectory.cleanup_all()

    def create_zip(self, zip_file_name, zip_docx_file_name):
        zip_file = os.path.join(self.temp_directory.path, zip_file_name)
        docx_file = "tests/fixtures/letterparser/sections.docx"
        with zipfile.ZipFile(zip_file, "w") as open_zip:
            open_zip.write(docx_file, zip_docx_file_name)
        return zip_file

    def test_check_input(self):
        file_name = "tests/files_source/elife-39122.zip"
        error_messages = letterparser_provider.check_input(file_name)
        self.assertEqual(len(error_messages), 0)

    def test_check_input_none(self):
        file_name = None
        error_messages = letterparser_provider.check_input(file_name)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], "File None does not exist")

    def test_check_input_file_name(self):
        file_name = "not_a_zip.docx"
        error_messages = letterparser_provider.check_input(file_name)
        self.assertEqual(len(error_messages), 2)
        self.assertEqual(
            error_messages[0], "File %s name does not end in .zip" % file_name
        )
        self.assertEqual(
            error_messages[1], "File %s is not a valid zip file" % file_name
        )

    def test_check_input_zip_subfolder(self):
        zip_file_name = "elife-00666.zip"
        zip_docx_file_name = "subfolder/elife-00666.docx"
        zip_file = self.create_zip(zip_file_name, zip_docx_file_name)

        error_messages = letterparser_provider.check_input(zip_file)
        self.assertEqual(len(error_messages), 2)
        self.assertEqual(
            error_messages[0],
            "Could not find .docx file in zip file %s" % zip_file_name,
        )
        self.assertEqual(
            error_messages[1],
            "Note: .docx file %s may be in a subfolder in zip file %s"
            % (zip_docx_file_name, zip_file_name),
        )

    def test_check_input_docx_file_name(self):
        """a mansucript ID cannot be found from the .docx file name"""
        zip_file_name = "elife-00666.zip"
        zip_docx_file_name = "elife-00666 edit.docx"
        zip_file = self.create_zip(zip_file_name, zip_docx_file_name)

        error_messages = letterparser_provider.check_input(zip_file)
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(
            error_messages[0],
            "Cannot get manuscript ID from %s inside %s"
            % (zip_docx_file_name, zip_file_name),
        )


class TestProcessZip(unittest.TestCase):
    def setUp(self):
        self.temp_directory = TempDirectory()
        self.temp_dir = self.temp_directory.path
        self.config = letterparser_provider.letterparser_config(settings_mock)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_process_zip(self):
        file_name = "tests/files_source/elife-39122.zip"
        (
            articles,
            asset_file_names,
            statuses,
            error_messages,
        ) = letterparser_provider.process_zip(
            file_name, config=self.config, temp_dir=self.temp_dir
        )
        self.assertEqual(len(articles), 2)
        self.assertEqual(statuses.get("unzip"), True)
        self.assertEqual(statuses.get("build"), True)
        self.assertEqual(statuses.get("valid"), True)
        self.assertEqual(len(error_messages), 0)
        simple_asset_file_names = [
            asset.split(os.sep)[-1] for asset in asset_file_names
        ]
        self.assertEqual(
            simple_asset_file_names,
            ["elife-39122-sa2-fig1.jpg", "elife-39122-sa2-fig2.jpg"],
        )

    def test_process_articles_to_xml(self):
        file_name = "tests/files_source/elife-39122.zip"
        (
            articles,
            asset_file_names,
            statuses,
            error_messages,
        ) = letterparser_provider.process_zip(
            file_name, config=self.config, temp_dir=self.temp_dir
        )
        xml_string, statuses = letterparser_provider.process_articles_to_xml(
            articles, self.temp_dir
        )
        self.assertEqual(statuses.get("generate"), True)
        self.assertEqual(statuses.get("output"), True)
        self.assertTrue(b"10.7554/eLife.39122.sa2" in xml_string)


class TestManuscriptFromArticles(unittest.TestCase):
    def test_manuscript_from_articles(self):
        manuscript = 666
        article = Article()
        article.manuscript = manuscript
        self.assertEqual(
            letterparser_provider.manuscript_from_articles([article]), manuscript
        )

    def test_manuscript_from_articles_none(self):
        self.assertEqual(letterparser_provider.manuscript_from_articles(None), None)


class TestArticleDoiFromXml(unittest.TestCase):
    def test_article_doi_from_xml(self):
        xml_string = "<article-id>10.7554/eLife.39122.sa1"
        self.assertEqual(
            letterparser_provider.article_doi_from_xml(xml_string),
            "10.7554/eLife.39122",
        )
