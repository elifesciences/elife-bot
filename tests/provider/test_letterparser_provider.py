# coding=utf-8

import unittest
import provider.letterparser_provider as letterparser_provider


class TestLetterParserProvider(unittest.TestCase):

    def test_parse_file(self):
        """test parsing docx file with pandoc which may be called via Docker"""
        file_name = 'tests/fixtures/letterparser/sections.docx'
        # blank config will use pandoc executable if present, otherwise via Docker image default
        config = {}
        expected = (
            '<p><bold>Preamble<break /></bold></p>\n'
            '<p>Preamble ....</p>\n'
            '<p><bold>Decision letter</bold></p>\n'
            '<p>Decision letter ....</p>\n'
            '<p><bold>Author response</bold></p>\n'
            '<p>Author response ....</p>\n')

        output = letterparser_provider.parse_file(file_name, config)
        self.assertEqual(output, expected, 'Docker pandoc output not equal, is Docker running?')
