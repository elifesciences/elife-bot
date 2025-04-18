# coding=utf-8

import unittest
import json
import os
import shutil
import datetime
import arrow
from testfixtures import tempdir
from testfixtures import TempDirectory
from mock import patch
from ddt import ddt, data, unpack
from provider import ejp, utils
from provider.ejp import EJP
from tests import settings_mock
from tests.activity.classes_mock import FakeStorageContext


@ddt
class TestProviderEJP(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.ejp = EJP(settings_mock, tmp_dir=self.directory.path)
        self.author_column_headings = [
            "ms_no",
            "author_seq",
            "first_nm",
            "last_nm",
            "author_type_cde",
            "dual_corr_author_ind",
            "e_mail",
        ]
        self.preprint_author_column_headings = [
            "ms_no",
            "ms_rev_no",
            "appeal_ind",
            "author_seq",
            "first_nm",
            "last_nm",
            "author_type_cde",
            "dual_corr_author_ind",
            "e_mail",
            "primary_org",
        ]

    def tearDown(self):
        TempDirectory.cleanup_all()

    @tempdir()
    @data(
        (None, "", "wb", TypeError, None),
        ("read_mode_failure.txt", "", "r", IOError, None),
        ("good.txt", "good", "wb", None, "good.txt"),
    )
    @unpack
    def test_write_content_to_file(
        self, filename, content, mode, exception_raised, expected_document
    ):
        # if we expect a document, for comparison we need to add the tmp_dir path to it
        if expected_document:
            expected_document = os.path.join(self.directory.path, expected_document)
        try:
            document = self.ejp.write_content_to_file(filename, content, mode)
            # check the returned value
            self.assertEqual(document, expected_document)
        except:
            # check the exception
            if exception_raised:
                self.assertRaises(exception_raised)

    @patch("provider.ejp.storage_context")
    @patch("provider.ejp.EJP.find_latest_s3_file_name")
    @data(
        (
            3,
            False,
            [
                [
                    "3",
                    "1",
                    "Author",
                    "One",
                    "Contributing Author",
                    " ",
                    "author01@example.com",
                ],
                [
                    "3",
                    "2",
                    "Author",
                    "Two",
                    "Contributing Author",
                    " ",
                    "author02@example.org",
                ],
            ],
        ),
        (
            3,
            True,
            [
                [
                    "3",
                    "3",
                    "Author",
                    "Three",
                    "Corresponding Author",
                    " ",
                    "author03@example.com",
                ]
            ],
        ),
        (
            13,
            False,
            [
                [
                    "13",
                    "1",
                    "Author",
                    "Uno",
                    "Contributing Author",
                    " ",
                    "author13-01@example.com",
                ],
                [
                    "13",
                    "2",
                    "Author",
                    "Dos",
                    "Contributing Author",
                    " ",
                    "author13-02@example.com",
                ],
            ],
        ),
        (
            "00003",
            True,
            [
                [
                    "3",
                    "3",
                    "Author",
                    "Three",
                    "Corresponding Author",
                    " ",
                    "author03@example.com",
                ]
            ],
        ),
        (666, True, None),
        (
            None,
            None,
            [
                [
                    "3",
                    "1",
                    "Author",
                    "One",
                    "Contributing Author",
                    " ",
                    "author01@example.com",
                ],
                [
                    "3",
                    "2",
                    "Author",
                    "Two",
                    "Contributing Author",
                    " ",
                    "author02@example.org",
                ],
                [
                    "3",
                    "3",
                    "Author",
                    "Three",
                    "Corresponding Author",
                    " ",
                    "author03@example.com",
                ],
                [
                    "13",
                    "1",
                    "Author",
                    "Uno",
                    "Contributing Author",
                    " ",
                    "author13-01@example.com",
                ],
                [
                    "13",
                    "2",
                    "Author",
                    "Dos",
                    "Contributing Author",
                    " ",
                    "author13-02@example.com",
                ],
                [
                    "13",
                    "3",
                    "Authoré",
                    "Trés",
                    "Contributing Author",
                    "1",
                    "author13-03@example.com",
                ],
                [
                    "13",
                    "4",
                    "Author",
                    "Cuatro",
                    "Corresponding Author",
                    " ",
                    "author13-04@example.com",
                ],
            ],
        ),
    )
    @unpack
    def test_get_authors(
        self,
        doi_id,
        corresponding,
        expected_authors,
        fake_find_latest,
        fake_storage_context,
    ):
        author_csv_s3_object = (
            "ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_06_10_eLife.csv"
        )
        fake_find_latest.return_value = author_csv_s3_object
        # copy the sample csv file to the temp directory
        s3_key_name = os.path.join(self.directory.path, author_csv_s3_object)
        shutil.copy(
            os.path.join("tests", "test_data", "ejp_author_file.csv"), s3_key_name
        )
        # populate the storage provider with the CSV file
        resources = [s3_key_name]
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, resources
        )
        # call the function
        (column_headings, authors) = self.ejp.get_authors(doi_id, corresponding)
        # assert results
        self.assertEqual(column_headings, self.author_column_headings)
        self.assertEqual(authors, expected_authors)

    @patch("provider.ejp.storage_context")
    @patch("provider.ejp.EJP.find_latest_s3_file_name")
    @data(
        (86939, 1, 14),
        (86939, 2, 14),
        (91826, 1, 5),
        ("91826", "2", 5),
        (91826, 3, None),
        (91826, None, None),
        (666, 1, None),
    )
    @unpack
    def test_get_preprint_authors(
        self,
        doi_id,
        version,
        expected_author_count,
        fake_find_latest,
        fake_storage_context,
    ):
        "test getting preprint authors from a CSV file"
        preprint_author_csv_s3_object = (
            "ejp_query_tool_query_id_Production_data_04_-_"
            "Reviewed_preprint_author_details_2024_01_29_eLife-rp.csv"
        )
        fake_find_latest.return_value = preprint_author_csv_s3_object
        # copy the sample csv file to the temp directory
        s3_key_name = os.path.join(self.directory.path, preprint_author_csv_s3_object)
        shutil.copy(
            os.path.join("tests", "test_data", "ejp_preprint_author_file.csv"),
            s3_key_name,
        )
        # populate the storage provider with the CSV file
        resources = [s3_key_name]
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, resources
        )
        # call the function
        (column_headings, authors) = self.ejp.get_preprint_authors(doi_id, version)
        # assert results
        self.assertEqual(column_headings, self.preprint_author_column_headings)
        if authors is None:
            self.assertEqual(
                authors,
                expected_author_count,
                "failed for doi_id %s, version %s" % (doi_id, version),
            )
        else:
            self.assertEqual(
                len(authors),
                expected_author_count,
                "failed for doi_id %s, version %s" % (doi_id, version),
            )

    @patch.object(arrow, "utcnow")
    @patch("provider.ejp.storage_context")
    @data(
        (
            "author",
            "ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_06_10_eLife.csv",
        ),
        (
            "preprint_author",
            (
                "ejp_query_tool_query_id_Production_data_04_-_"
                "Reviewed_preprint_author_details_2019_06_10_elife-rp.csv"
            ),
        ),
        (
            "poa_manuscript",
            "ejp_query_tool_query_id_POA_Manuscript_2019_06_10_eLife.csv",
        ),
        ("poa_author", "ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv"),
        ("poa_license", "ejp_query_tool_query_id_POA_License_2019_06_10_eLife.csv"),
        (
            "poa_subject_area",
            "ejp_query_tool_query_id_POA_Subject_Area_2019_06_10_eLife.csv",
        ),
        ("poa_received", "ejp_query_tool_query_id_POA_Received_2019_06_10_eLife.csv"),
        (
            "poa_research_organism",
            "ejp_query_tool_query_id_POA_Research_Organism_2019_06_10_eLife.csv",
        ),
        ("poa_abstract", "ejp_query_tool_query_id_POA_Abstract_2019_06_10_eLife.csv"),
        ("poa_title", "ejp_query_tool_query_id_POA_Title_2019_06_10_eLife.csv"),
        ("poa_keywords", "ejp_query_tool_query_id_POA_Keywords_2019_06_10_eLife.csv"),
        (
            "poa_group_authors",
            "ejp_query_tool_query_id_POA_Group_Authors_2019_06_10_eLife.csv",
        ),
        ("poa_datasets", "ejp_query_tool_query_id_POA_Datasets_2019_06_10_eLife.csv"),
        ("poa_funding", "ejp_query_tool_query_id_POA_Funding_2019_06_10_eLife.csv"),
        ("poa_ethics", "ejp_query_tool_query_id_POA_Ethics_2019_06_10_eLife.csv"),
    )
    @unpack
    def test_find_latest_s3_file_name_by_convention(
        self,
        file_type,
        expected_s3_key_name,
        fake_storage_context,
        fake_utcnow,
    ):
        """test finding latest CSV file names by their expected file name"""
        # add file to the mock bucket folder
        with open(
            os.path.join(self.directory.path, expected_s3_key_name), "wb"
        ) as open_file:
            open_file.write(b"test")
        resources = [expected_s3_key_name]
        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, resources
        )
        fake_utcnow.return_value = arrow.arrow.Arrow(2019, 6, 10)
        # call the function
        s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
        # assert results
        self.assertEqual(s3_key_name, expected_s3_key_name)

    @patch("provider.ejp.EJP.latest_s3_file_name_by_convention")
    @patch("provider.ejp.EJP.ejp_bucket_file_list")
    @data(
        (
            "author",
            "ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_06_10_eLife.csv",
        ),
        (
            "poa_manuscript",
            "ejp_query_tool_query_id_POA_Manuscript_2019_06_10_eLife.csv",
        ),
        ("poa_author", "ejp_query_tool_query_id_POA_Author_2019_06_10_eLife.csv"),
        ("poa_license", "ejp_query_tool_query_id_POA_License_2019_06_10_eLife.csv"),
        (
            "poa_subject_area",
            "ejp_query_tool_query_id_POA_Subject_Area_2019_06_10_eLife.csv",
        ),
        ("poa_received", "ejp_query_tool_query_id_POA_Received_2019_06_10_eLife.csv"),
        (
            "poa_research_organism",
            "ejp_query_tool_query_id_POA_Research_Organism_2019_06_10_eLife.csv",
        ),
        ("poa_abstract", "ejp_query_tool_query_id_POA_Abstract_2019_06_10_eLife.csv"),
        ("poa_title", "ejp_query_tool_query_id_POA_Title_2019_06_10_eLife.csv"),
        ("poa_keywords", "ejp_query_tool_query_id_POA_Keywords_2019_06_10_eLife.csv"),
        (
            "poa_group_authors",
            "ejp_query_tool_query_id_POA_Group_Authors_2019_06_10_eLife.csv",
        ),
        ("poa_datasets", "ejp_query_tool_query_id_POA_Datasets_2019_06_10_eLife.csv"),
        ("poa_funding", "ejp_query_tool_query_id_POA_Funding_2019_06_10_eLife.csv"),
        ("poa_ethics", "ejp_query_tool_query_id_POA_Ethics_2019_06_10_eLife.csv"),
    )
    @unpack
    def test_find_latest_s3_file_name_new(
        self,
        file_type,
        expected_s3_key_name,
        fake_ejp_bucket_file_list,
        fake_by_convention,
    ):
        """from new file naming find the latest CSV file names"""
        fake_by_convention.return_value = None
        bucket_list_file_new = os.path.join(
            "tests", "test_data", "ejp_bucket_list_new.json"
        )
        # mock things
        ejp_bucket_file_list = []
        with open(bucket_list_file_new, "r", encoding="utf-8") as open_file:
            ejp_bucket_file_list += json.loads(open_file.read())
        fake_ejp_bucket_file_list.return_value = ejp_bucket_file_list
        # call the function
        s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
        # assert results
        self.assertEqual(s3_key_name, expected_s3_key_name)

    @patch("provider.ejp.storage_context")
    def test_ejp_bucket_file_list(self, fake_storage_context):
        bucket_list_file_new = os.path.join(
            "tests", "test_data", "ejp_bucket_list_new.json"
        )
        ejp_bucket_file_list = []
        with open(bucket_list_file_new, "r", encoding="utf-8") as open_file:
            ejp_bucket_file_list += json.loads(open_file.read())
        resources = [
            {
                "Key": s3_file.get("name"),
                "LastModified": datetime.datetime.strptime(
                    s3_file.get("last_modified"), utils.DATE_TIME_FORMAT
                ),
            }
            for s3_file in ejp_bucket_file_list
        ]

        fake_storage_context.return_value = FakeStorageContext(
            self.directory.path, resources
        )
        bucket_list = self.ejp.ejp_bucket_file_list()
        self.assertEqual(len(bucket_list), 32)
        self.assertEqual(
            bucket_list[0],
            {
                "name": "ejp_query_tool_query_id_15a)_Accepted_Paper_Details_2019_05_31_eLife.csv",
                "last_modified": "2019-05-31T00:00:00.000Z",
                "last_modified_timestamp": 1559260800,
            },
        )


class TestAuthorDetailList(unittest.TestCase):
    def setUp(self):
        self.author_csv_file = os.path.join("tests", "test_data", "ejp_author_file.csv")

    def test_author_detail_list(self):
        corresponding = None
        column_headings, authors = ejp.author_detail_list(
            self.author_csv_file, 13, corresponding
        )
        self.assertEqual(len(authors), 4)

    def test_author_detail_list_corresponding_true(self):
        corresponding = True
        column_headings, authors = ejp.author_detail_list(
            self.author_csv_file, 13, corresponding
        )
        self.assertEqual(len(authors), 2)

    def test_author_detail_list_corresponding_false(self):
        corresponding = False
        column_headings, authors = ejp.author_detail_list(
            self.author_csv_file, 13, corresponding
        )
        self.assertEqual(len(authors), 2)


class TestParseAuthorFile(unittest.TestCase):
    def test_parse_author_file(self):
        author_csv_file = os.path.join("tests", "test_data", "ejp_author_file.csv")
        expected = [
            "ms_no",
            "author_seq",
            "first_nm",
            "last_nm",
            "author_type_cde",
            "dual_corr_author_ind",
            "e_mail",
        ]
        # call the function
        (column_headings, authors) = ejp.parse_author_file(author_csv_file)
        # assert results
        self.assertEqual(column_headings, expected)
        self.assertTrue(len(authors) > 0)


@ddt
class TestPreprintAuthorDetailList(unittest.TestCase):
    def setUp(self):
        self.author_csv_file = os.path.join(
            "tests", "test_data", "ejp_preprint_author_file.csv"
        )

    @data(
        {"article_id": 86939, "version": 1, "expected": 14},
        {"article_id": 86939, "version": 2, "expected": 14},
        {"article_id": 91826, "version": 1, "expected": 5},
        {"article_id": 91826, "version": "2", "expected": 5},
    )
    def test_preprint_author_detail_list(self, test_data):
        column_headings, authors = ejp.preprint_author_detail_list(
            self.author_csv_file, test_data.get("article_id"), test_data.get("version")
        )
        self.assertEqual(len(column_headings), 10)
        self.assertEqual(len(authors), test_data.get("expected"))


class TestParsePreprintAuthorFile(unittest.TestCase):
    def test_parse_preprint_author_file(self):
        author_csv_file = os.path.join(
            "tests", "test_data", "ejp_preprint_author_file.csv"
        )
        expected = [
            "ms_no",
            "ms_rev_no",
            "appeal_ind",
            "author_seq",
            "first_nm",
            "last_nm",
            "author_type_cde",
            "dual_corr_author_ind",
            "e_mail",
            "primary_org",
        ]
        # call the function
        (column_headings, authors) = ejp.parse_preprint_author_file(author_csv_file)
        # assert results
        self.assertEqual(column_headings, expected)
        self.assertTrue(len(authors) > 0)
