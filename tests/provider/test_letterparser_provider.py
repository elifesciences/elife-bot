# coding=utf-8

import unittest
import docker
from mock import patch
from elifearticle.article import Article
import tests.settings_mock as settings_mock
import provider.letterparser_provider as letterparser_provider


class TestLetterParserProvider(unittest.TestCase):

    def setUp(self):
        self.file_name = 'tests/fixtures/letterparser/sections.docx'
        self.blank_config = {}

    def test_letterparser_config(self):
        """test reading the letterparser config file"""
        config = letterparser_provider.letterparser_config(settings_mock)
        self.assertEqual(config.get("docker_image"), "elifesciences/pandoc:2.7")

    def test_parse_file(self):
        """test parsing docx file with pandoc which may be called via Docker"""
        # blank config will use pandoc executable if present, otherwise via Docker image default
        expected = (
            '<p><bold>Preamble<break /></bold></p>\n'
            '<p>Preamble ....</p>\n'
            '<p><bold>Decision letter</bold></p>\n'
            '<p>Decision letter ....</p>\n'
            '<p><bold>Author response</bold></p>\n'
            '<p>Author response ....</p>\n')

        output = letterparser_provider.parse_file(self.file_name, self.blank_config)
        self.assertEqual(output, expected, 'Docker pandoc output not equal, is Docker running?')

    @patch('letterparser.parse.parse_file')
    def test_parse_file_docker_exception(self, fake_letterparser_parse):
        fake_letterparser_parse.side_effect = docker.errors.APIError('Fake exception')
        with self.assertRaises(docker.errors.APIError):
            letterparser_provider.parse_file(self.file_name, self.blank_config)

    @patch('letterparser.parse.parse_file')
    def test_parse_file_other_exception(self, fake_letterparser_parse):
        fake_letterparser_parse.side_effect = Exception('Other fake exception')
        with self.assertRaises(Exception):
            letterparser_provider.parse_file(self.file_name, self.blank_config)


class TestValidateArticles(unittest.TestCase):

    def test_validate_articles_valid(self):
        """test two articles that are completely valid"""
        articles = [
            Article(
                '10.7554/eLife.99999.sa1',
                'Decision letter: Test',
                ),
            Article(
                '10.7554/eLife.99999.sa2',
                'Author response: Test',
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
        """test one article which is not enough"""
        articles = [Article()]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertFalse(valid)
        self.assertTrue(len(error_messages) > 0)

    def test_validate_articles_doi(self):
        """test article missing a DOI"""
        articles = [Article(), Article()]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertFalse(valid)
        self.assertTrue(len(error_messages) > 0)

    def test_validate_articles_no_titles(self):
        """test two articles without titles"""
        articles = [Article('10.7554/eLife.99999.sa1'), Article('10.7554/eLife.99999.sa2')]
        valid, error_messages = letterparser_provider.validate_articles(articles)
        self.assertFalse(valid)
        self.assertTrue(len(error_messages) > 0)
