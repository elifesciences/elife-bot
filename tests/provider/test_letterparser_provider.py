# coding=utf-8

import unittest
import provider.letterparser_provider as letterparser_provider


class TestLetterParserProvider(unittest.TestCase):

    def test_docker_pandoc_output(self):
        """test calling pandoc via Docker"""
        file_name = 'tests/fixtures/letterparser/sections.docx'
        # fake config for specifying Docker image
        config = {'docker_image': 'pandoc/core:2.6'}
        expected = (
            '<p><bold>Preamble<break /></bold></p>\n'
            '<p>Preamble ....</p>\n'
            '<p><bold>Decision letter</bold></p>\n'
            '<p>Decision letter ....</p>\n'
            '<p><bold>Author response</bold></p>\n'
            '<p>Author response ....</p>\n')

        output = letterparser_provider.docker_pandoc_output(file_name, config)
        self.assertEqual(output, expected, 'Docker pandoc output not equal, is Docker running?')
