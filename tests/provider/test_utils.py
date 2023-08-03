# coding=utf-8

import unittest
import time
import sys
import arrow
from mock import patch
from ddt import ddt, data, unpack
import provider.utils as utils


@ddt
class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    @unpack
    @data(
        (7, "00007"),
        ("7", "00007"),
    )
    def test_pad_msid(self, msid, expected):
        self.assertEqual(utils.pad_msid(msid), expected)

    @unpack
    @data(
        (2, "02"),
        ("2", "02"),
    )
    def test_pad_volume(self, volume, expected):
        self.assertEqual(utils.pad_volume(volume), expected)

    @unpack
    @data(
        ("clean", "clean"),
        ("  very \n   messy  ", "very messy"),
    )
    def test_tidy_whitespace(self, string, expected):
        self.assertEqual(utils.tidy_whitespace(string), expected)

    @unpack
    @data(
        (None, "VOR"),
        (True, "POA"),
        (False, "VOR"),
        ("Anything", "POA"),
    )
    def test_article_status(self, value, expected):
        self.assertEqual(utils.article_status(value), expected)

    def test_msid_from_doi(self):
        cases = [
            ("10.7554/eLife.09560", 9560),
            # component
            ("10.7554/eLife.09560.sa0", 9560),
            # versioned
            ("10.7554/eLife.09560.1", 9560),
            ("10.7554/eLife.09560.1.sa0", 9560),
            # testing msid
            ("10.7554/eLife.97832421234567890", 97832421234567890),
            # case insensitive
            ("10.7554/ELIFE.09560", 9560),
            # URL format
            ("https://doi.org/10.7554/eLife.09560.1.sa0", 9560),
            # unlikely cases
            ("10.7554/eLife.0", 0),
            ("10.7554/eLife.0.1", 0),
            ("10.7554/eLife.0.1.2.3.4", 0),
            # no match cases
            (None, None),
            ("", None),
            ([], None),
            ({}, None),
            ("not_a_doi", None),
        ]
        for given, expected in cases:
            self.assertEqual(
                utils.msid_from_doi(given), expected, "failed case %r" % given
            )

    @unpack
    @data(
        (None, None, None),
        ("2018", None, 7),
        (2018, 2020, -2),
    )
    def test_volume_from_year(self, year, start_year, expected):
        if start_year:
            self.assertEqual(utils.volume_from_year(year, start_year), expected)
        else:
            self.assertEqual(utils.volume_from_year(year), expected)

    @unpack
    @data(
        (None, None, None),
        ("2018-01-01", None, 7),
        ("2018-01-01", 2020, -2),
    )
    def test_volume_from_pub_date(self, pub_date_str, start_year, expected):
        pub_date = None
        if pub_date_str:
            pub_date = time.strptime(pub_date_str, "%Y-%m-%d")
        if start_year:
            self.assertEqual(utils.volume_from_pub_date(pub_date, start_year), expected)
        else:
            self.assertEqual(utils.volume_from_pub_date(pub_date), expected)

    @unpack
    @data(
        (None, None),
        ("file_name.jpg", "file_name.jpg"),
        ("file+name.jpg", "file name.jpg"),
    )
    def test_unquote_plus(self, value, expected):
        self.assertEqual(utils.unquote_plus(value), expected)

    @unpack
    @data(
        (None, None, type(None)),
        ("", "", str),
        ("tmp/foldér", "tmp/foldér", str),
        (b"tmp/folde\xcc\x81r", "tmp/foldér", str),
    )
    def test_unicode_encode(self, value, expected, expected_type):
        encoded_value = utils.unicode_encode(value)
        self.assertEqual(encoded_value, expected)
        self.assertEqual(type(encoded_value), expected_type)

    @patch.object(arrow, "utcnow")
    def test_set_datestamp(self, fake_utcnow):
        fake_utcnow.return_value = arrow.arrow.Arrow(2021, 1, 1)
        expected = "20210101"
        self.assertEqual(utils.set_datestamp(), expected)

    @patch.object(arrow, "utcnow")
    def test_set_datestamp_glued(self, fake_utcnow):
        fake_utcnow.return_value = arrow.arrow.Arrow(2021, 1, 1)
        glue = "_"
        expected = "2021_01_01"
        self.assertEqual(utils.set_datestamp(glue), expected)

    def test_get_doi_url(self):
        doi_url = utils.get_doi_url("10.7554/eLife.08411")
        self.assertEqual(doi_url, "https://doi.org/10.7554/eLife.08411")

    def test_doi_uri_to_doi(self):
        doi = "10.1101/2021.06.02.446694"
        doi_url = "https://doi.org/%s" % doi
        self.assertEqual(utils.doi_uri_to_doi(doi_url), doi)


class TestSettingsEnvironment(unittest.TestCase):
    "test for utils.settings_environment()"

    def test_settings_environment(self):
        "test returning settings class name"

        class ci:
            "mock settings object for testing"
            pass

        settings_object = ci
        result = utils.settings_environment(ci)
        self.assertEqual(result, "ci")

    def test_not_callable(self):
        "test if settings is not a class"
        result = utils.settings_environment(None)
        self.assertEqual(result, None)


class TestConsoleStart(unittest.TestCase):
    def test_console_start(self):
        env = "foo"
        expected = env
        testargs = ["cron.py", "-e", env]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env(), expected)

    def test_console_start_blank(self):
        expected = "dev"
        testargs = ["cron.py"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env(), expected)

    def test_console_unrecognized_arguments(self):
        env = "foo"
        expected = env
        testargs = ["cron.py", "-e", env, "0"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env(), expected)


class TestConsoleStartEnvDoiId(unittest.TestCase):
    def test_console_start_env_doi_id(self):
        env = "foo"
        doi_id = "7"
        expected = env, doi_id
        testargs = ["cron.py", "-e", env, "-d", doi_id]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_doi_id(), expected)

    def test_console_start_env_doi_id_blank(self):
        expected = "dev", None
        testargs = ["cron.py"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_doi_id(), expected)

    def test_console_start_env_doi_id_unrecognized_arguments(self):
        env = "foo"
        expected = env, None
        testargs = ["cron.py", "-e", env, "0"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_doi_id(), expected)


class TestConsoleStartEnvDocument(unittest.TestCase):
    def test_console_start_env_document(self):
        env = "foo"
        document = "elife-00666-vor-v1-20210914000000.zip"
        expected = env, document
        testargs = ["cron.py", "-e", env, "-f", document]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_document(), expected)

    def test_console_start_env_document_blank(self):
        expected = "dev", None
        testargs = ["cron.py"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_document(), expected)

    def test_console_start_env_document_unrecognized_arguments(self):
        env = "foo"
        expected = env, None
        testargs = ["cron.py", "-e", env, "0"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_document(), expected)


class TestConsoleStartEnvWorkflow(unittest.TestCase):
    def test_console_start_env_workflow(self):
        env = "foo"
        workflow = "HEFCE"
        expected = env, workflow
        testargs = ["cron.py", "-e", env, "-w", workflow]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow(), expected)

    def test_console_start_env_workflow_blank(self):
        expected = "dev", None
        testargs = ["cron.py"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow(), expected)

    def test_console_start_env_workflow_unrecognized_arguments(self):
        env = "foo"
        expected = env, None
        testargs = ["cron.py", "-e", env, "0"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow(), expected)


class TestConsoleStartEnvWorkflowDoiId(unittest.TestCase):
    def test_console_start_env_workflow_doi_id(self):
        env = "foo"
        doi_id = "7"
        workflow = "HEFCE"
        expected = env, doi_id, workflow
        testargs = ["cron.py", "-e", env, "-d", doi_id, "-w", workflow]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow_doi_id(), expected)

    def test_console_start_env_workflow_doi_id_blank(self):
        expected = "dev", None, None
        testargs = ["cron.py"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow_doi_id(), expected)

    def test_console_start_env_workflow_doi_id_unrecognized_arguments(self):
        env = "foo"
        expected = env, None, None
        testargs = ["cron.py", "-e", env, "0"]
        with patch.object(sys, "argv", testargs):
            self.assertEqual(utils.console_start_env_workflow_doi_id(), expected)


@ddt
class TestContentTypeFromFileName(unittest.TestCase):
    @unpack
    @data(
        (None, None),
        ("image.jpg", "image/jpeg"),
        ("/folder/file.test.pdf", "application/pdf"),
        ("/folder/weird_file.wdl", "binary/octet-stream"),
        ("a_file", "binary/octet-stream"),
    )
    def test_content_type_from_file_name(self, input, expected):
        result = utils.content_type_from_file_name(input)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
