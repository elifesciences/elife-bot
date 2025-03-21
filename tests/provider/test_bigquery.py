import unittest
import datetime
from mock import patch
from google.cloud.bigquery import Client
from google.cloud._helpers import UTC
from google.auth.exceptions import DefaultCredentialsError
from provider import bigquery
from tests.activity.classes_mock import FakeLogger
from tests.classes_mock import FakeBigQueryClient, FakeBigQueryRowIterator
from tests import bigquery_test_data, bigquery_preprint_test_data, settings_mock


class TestBigQueryProvider(unittest.TestCase):
    @patch("google.auth.default")
    def test_get_client(self, fake_account_info):
        """mocked client for test coverage"""
        fake_account_info.return_value = None, None
        client = bigquery.get_client(settings_mock, FakeLogger())
        self.assertTrue(isinstance(client, Client))

    @patch("google.cloud.bigquery.Client.__init__")
    @patch("google.auth.crypt.RSASigner.from_service_account_info")
    def test_get_client_exception(self, fake_account_info, fake_init):
        """test coverage for credentials error exception"""
        fake_init.side_effect = DefaultCredentialsError()
        fake_account_info.return_value = None
        with self.assertRaises(DefaultCredentialsError):
            bigquery.get_client(settings_mock, FakeLogger())

    def test_article_query(self):
        expected = (
            "SELECT * FROM `elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit` "
            "WHERE DOI = @doi"
        )
        query = bigquery.article_query()
        self.assertEqual(query, expected)

    def test_article_data(self):
        rows = FakeBigQueryRowIterator([bigquery_test_data.ARTICLE_RESULT_15747])
        client = FakeBigQueryClient(rows)
        doi = "10.7554/eLife.15747"
        expected_doi = doi
        expected_decision_letter_timestamp_str = "2016-05-31 11:31:01+00:00"
        expected_last_name_list = ["Baldwin", "Bergstrom"]
        # run the query
        result = bigquery.article_data(client, doi)
        # check the result
        for row in result:
            self.assertEqual(row.DOI, expected_doi)
            self.assertEqual(
                str(row.Review_Comment_UTC_Timestamp),
                expected_decision_letter_timestamp_str,
            )
            names = []
            for editor in row.Reviewers_And_Editors:
                names.append(editor.get("Last_Name"))
            self.assertEqual(names, expected_last_name_list)

    def test_get_review_date(self):
        manuscript = bigquery.Manuscript()
        manuscript.decision_letter_datetime = datetime.datetime(
            2016, 5, 31, 11, 31, 1, tzinfo=UTC
        )
        manuscript.author_response_datetime = datetime.datetime(
            2016, 6, 10, 6, 28, 43, tzinfo=UTC
        )
        self.assertEqual(
            bigquery.get_review_date(manuscript, "article-commentary"), "2016-05-31"
        )
        self.assertEqual(
            bigquery.get_review_date(manuscript, "decision-letter"), "2016-05-31"
        )
        self.assertEqual(
            bigquery.get_review_date(manuscript, "editor-report"), "2016-05-31"
        )
        self.assertEqual(bigquery.get_review_date(manuscript, "reply"), "2016-06-10")
        self.assertEqual(
            bigquery.get_review_date(manuscript, "referee-report"), "2016-05-31"
        )

    def test_get_review_date_no_author_response_datetime(self):
        manuscript = bigquery.Manuscript()
        manuscript.decision_letter_datetime = datetime.datetime(
            2016, 5, 31, 11, 31, 1, tzinfo=UTC
        )
        manuscript.author_response_datetime = None
        self.assertEqual(
            bigquery.get_review_date(manuscript, "article-commentary"), "2016-05-31"
        )
        self.assertEqual(
            bigquery.get_review_date(manuscript, "decision-letter"), "2016-05-31"
        )
        self.assertEqual(bigquery.get_review_date(manuscript, "reply"), "2016-05-31")

    def test_get_review_date_none_manuscript(self):
        self.assertEqual(bigquery.get_review_date(None, None), None)


class TestPreprintArticleQuery(unittest.TestCase):
    def test_preprint_article_query(self):
        "test preprint_article_query()"
        date_string = "2023-11-28"
        day_interval = 7
        query = bigquery.preprint_article_query(date_string, day_interval)
        expected = (
            "SELECT * FROM "
            "`elife-data-pipeline.prod.v_latest_reviewed_preprint_publication_date` "
            "WHERE `publication_date` between DATE_SUB(@date_string, INTERVAL @day_interval DAY) "
            "AND @date_string "
            "ORDER BY publication_date DESC"
        )
        self.assertEqual(query, expected)

    def test_no_arguments(self):
        "test preprint_article_query() with no arguments supplied"
        query = bigquery.preprint_article_query()
        expected = (
            "SELECT * FROM "
            "`elife-data-pipeline.prod.v_latest_reviewed_preprint_publication_date` "
            " ORDER BY publication_date DESC"
        )
        self.assertEqual(query, expected)


class TestPreprintArticleResult(unittest.TestCase):
    "tests for bigquery.preprint_article_result()"

    def test_preprint_article_result(self):
        "test preprint_article_result()"
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        # run the query
        result = bigquery.preprint_article_result(client)
        # check the result
        rows = list(result)

        self.assertEqual(rows[0].elife_doi, "10.7554/eLife.92362")
        self.assertEqual(rows[0].elife_doi_version, 1)
        self.assertEqual(rows[0].publication_date, datetime.date(2023, 11, 22))
        self.assertEqual(rows[0].utc_publication_time, datetime.time(14, 0))

        self.assertEqual(rows[1].elife_doi, "10.7554/eLife.87445")
        self.assertEqual(rows[1].elife_doi_version, 2)
        self.assertEqual(rows[1].publication_date, datetime.date(2023, 11, 22))
        self.assertEqual(rows[1].utc_publication_time, datetime.time(14, 0))


class TestPreprintObjects(unittest.TestCase):
    "tests for bigquery.preprint_objects()"

    def test_preprint_article_result(self):
        "test preprint_article_result()"
        result = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        preprints = bigquery.preprint_objects(result)

        # assertions
        self.assertEqual(preprints[0].doi, "10.7554/eLife.92362")
        self.assertEqual(preprints[0].version, 1)
        self.assertEqual(preprints[0].publication_date, datetime.date(2023, 11, 22))
        self.assertEqual(preprints[0].utc_publication_time, datetime.time(14, 0))

        self.assertEqual(preprints[1].doi, "10.7554/eLife.87445")
        self.assertEqual(preprints[1].version, 2)
        self.assertEqual(preprints[1].publication_date, datetime.date(2023, 11, 22))
        self.assertEqual(preprints[1].utc_publication_time, datetime.time(14, 0))


class TestManuscript(unittest.TestCase):
    def test_manuscript_init(self):
        """instantiate a Manuscript object from row data"""
        manuscript = bigquery.Manuscript(bigquery_test_data.ARTICLE_RESULT_15747)
        self.assertEqual(manuscript.manuscript_id, "15747")
        self.assertEqual(manuscript.doi, "10.7554/eLife.15747")
        # check decision_letter_datetime
        self.assertEqual(
            manuscript.decision_letter_datetime,
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=UTC),
        )
        self.assertEqual(
            "2016-05-31", bigquery.date_to_string(manuscript.decision_letter_datetime)
        )
        # check author_response_datetime
        self.assertEqual(
            manuscript.author_response_datetime,
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=UTC),
        )
        self.assertEqual(
            "2016-06-10", bigquery.date_to_string(manuscript.author_response_datetime)
        )
        # check reviwers
        self.assertEqual(len(manuscript.reviewers), 2)
        # reviewer 1
        self.assertEqual(manuscript.reviewers[0].title, "Dr.")
        self.assertEqual(manuscript.reviewers[0].last_name, "Baldwin")
        self.assertEqual(manuscript.reviewers[0].middle_name, None)
        self.assertEqual(manuscript.reviewers[0].role, "Senior Editor")
        self.assertEqual(manuscript.reviewers[0].orcid, None)
        self.assertEqual(manuscript.reviewers[0].first_name, "Ian")
        self.assertEqual(manuscript.reviewers[0].person_id, "1013")
        # reviewer 2
        self.assertEqual(manuscript.reviewers[1].title, "")
        self.assertEqual(manuscript.reviewers[1].last_name, "Bergstrom")
        self.assertEqual(manuscript.reviewers[1].middle_name, None)
        self.assertEqual(manuscript.reviewers[1].role, "Reviewing Editor")
        self.assertEqual(manuscript.reviewers[1].orcid, None)
        self.assertEqual(manuscript.reviewers[1].first_name, "Carl")
        self.assertEqual(manuscript.reviewers[1].person_id, "1046")

    def test_manuscript_populate_from_row_none(self):
        """empty row data"""
        manuscript = bigquery.Manuscript()
        self.assertIsNone(manuscript.populate_from_row(None))


class TestReviewer(unittest.TestCase):
    def test_reviewer_populate_from_dict_none(self):
        """empty row data"""
        reviewer = bigquery.Reviewer()
        self.assertIsNone(reviewer.populate_from_dict(None))


class TestPreprint(unittest.TestCase):
    def test_preprint_init(self):
        "instantiate a Preprint object from row data"
        preprint = bigquery.Preprint(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT[0]
        )
        self.assertEqual(preprint.doi, "10.7554/eLife.92362")
        self.assertEqual(preprint.version, 1)
        self.assertEqual(preprint.publication_date, datetime.date(2023, 11, 22))
        self.assertEqual(preprint.utc_publication_time, datetime.time(14, 0))

    def test_preprint_populate_from_dict_none(self):
        "empty row data"
        preprint = bigquery.Preprint()
        self.assertIsNone(preprint.populate_from_dict(None))
