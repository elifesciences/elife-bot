import unittest
from ddt import ddt, data, unpack
from provider import s3lib


@ddt
class TestProviderS3Lib(unittest.TestCase):
    def setUp(self):
        pass

    @data(
        (["pmc/zip/elife-05-19405.zip"], [".zip"], ["pmc/zip/elife-05-19405.zip"]),
        (["pmc/zip/elife-05-19405.zip"], [".foo"], []),
        (["1", "a.1", "b.2", "c.3"], [".1", ".2"], ["a.1", "b.2"]),
    )
    @unpack
    def test_filter_list_by_file_extensions(
        self, s3_key_names, file_extensions, expected
    ):
        self.assertEqual(
            s3lib.filter_list_by_file_extensions(s3_key_names, file_extensions),
            expected,
        )

    @data(
        (99999, ["pmc/zip/elife-05-19405.zip"], None),
        (19405, ["pmc/zip/elife-05-19405.zip"], "pmc/zip/elife-05-19405.zip"),
        (
            24052,
            [
                "pmc/zip/elife-06-24052.zip",
                "pmc/zip/elife-06-24052.r1.zip",
                "pmc/zip/elife-06-24052.r2.zip",
            ],
            "pmc/zip/elife-06-24052.r2.zip",
        ),
        # strange example below would not normally exist but is for code coverage
        (
            24052,
            [
                "pmc/zip/elife-04-24052.zip",
                "pmc/zip/elife-05-24052.zip",
                "pmc/zip/elife-05-24052.r1.zip",
            ],
            "pmc/zip/elife-05-24052.r1.zip",
        ),
    )
    @unpack
    def test_latest_pmc_zip_revision(self, doi_id, s3_key_names, expected_s3_key_name):
        self.assertEqual(
            s3lib.latest_pmc_zip_revision(doi_id, s3_key_names), expected_s3_key_name
        )
