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

    @unpack
    @data((None, None), ("10.7554/eLife.00003", 3), ("not_a_doi", None))
    def test_msid_from_doi(self, value, expected):
        self.assertEqual(utils.msid_from_doi(value), expected)

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
        (u"", "", str),
        (u"tmp/foldér", "tmp/foldér", str),
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


if __name__ == "__main__":
    unittest.main()
