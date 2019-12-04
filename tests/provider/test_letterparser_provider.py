# coding=utf-8

import unittest
import docker
from mock import patch
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
