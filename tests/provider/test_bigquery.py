import unittest
import datetime
from mock import patch
from google.oauth2.service_account import Credentials
from google.cloud.bigquery import Client
from google.cloud._helpers import _UTC
from provider import bigquery
from tests.classes_mock import FakeBigQueryClient, FakeBigQueryRowIterator
from tests import bigquery_test_data, settings_mock


class TestBigQueryProvider(unittest.TestCase):

    @patch('google.auth.crypt.RSASigner.from_service_account_info')
    def test_get_credentials(self, fake_account_info):
        fake_account_info.return_value = None
        creds = bigquery.get_credentials(settings_mock)
        self.assertTrue(isinstance(creds, Credentials))

    @patch('google.auth.crypt.RSASigner.from_service_account_info')
    def test_get_client(self, fake_account_info):
        """mocked client for test coverage"""
        fake_account_info.return_value = None
        client = bigquery.get_client(settings_mock)
        self.assertTrue(isinstance(client, Client))

    def test_article_query(self):
        expected = (
            'SELECT * FROM `elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit` '
            'WHERE DOI = "10.7554/eLife.00666" ')
        query = bigquery.article_query('10.7554/eLife.00666')
        self.assertEqual(query, expected)

    def test_article_data(self):
        rows = FakeBigQueryRowIterator([bigquery_test_data.ARTICLE_RESULT_15747])
        client = FakeBigQueryClient(rows)
        doi = '10.7554/eLife.15747'
        expected_doi = doi
        expected_qc_complete_timestamp_str = '2016-05-31 11:31:01+00:00'
        expected_name_list = ['Ian Baldwin', 'Carl Bergstrom']
        # run the query
        result = bigquery.article_data(client, doi)
        # check the result
        for row in result:
            self.assertEqual(row.DOI, expected_doi)
            self.assertEqual(str(row.QC_Complete_Timestamp), expected_qc_complete_timestamp_str)
            names = []
            for editor in row.Reviewers_And_Editors:
                names.append(editor.get('Name'))
            self.assertEqual(names, expected_name_list)

    def test_get_review_date(self):
        manuscript = bigquery.Manuscript()
        manuscript.qc_complete_datetime = datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=_UTC())
        manuscript.decision_sent_datetime = datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=_UTC())
        self.assertEqual(bigquery.get_review_date(manuscript, 'article-commentary'), '2016-05-31')
        self.assertEqual(bigquery.get_review_date(manuscript, 'decision-letter'), '2016-05-31')
        self.assertEqual(bigquery.get_review_date(manuscript, 'reply'), '2016-06-10')

    def test_get_review_date_none_manuscript(self):
        self.assertEqual(bigquery.get_review_date(None, None), None)


class TestManuscript(unittest.TestCase):

    def test_manuscript_init(self):
        """"instantiate a Manuscript object from row data"""
        manuscript = bigquery.Manuscript(bigquery_test_data.ARTICLE_RESULT_15747)
        self.assertEqual(manuscript.manuscript_id, '15747')
        self.assertEqual(manuscript.doi, '10.7554/eLife.15747')
        # check qc_complete_datetime
        self.assertEqual(
            manuscript.qc_complete_datetime,
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=_UTC()))
        self.assertEqual('2016-05-31', bigquery.date_to_string(manuscript.qc_complete_datetime))
        # check decision_sent_datetime
        self.assertEqual(
            manuscript.decision_sent_datetime,
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=_UTC()))
        self.assertEqual('2016-06-10', bigquery.date_to_string(manuscript.decision_sent_datetime))
        # check reviwers
        self.assertEqual(len(manuscript.reviewers), 2)
        # reviewer 1
        self.assertEqual(manuscript.reviewers[0].name, 'Ian Baldwin')
        self.assertEqual(manuscript.reviewers[0].orcid, None)
        self.assertEqual(manuscript.reviewers[0].title, 'Dr.')
        self.assertEqual(manuscript.reviewers[0].person_id, '1013')
        self.assertEqual(manuscript.reviewers[0].roles, ['Senior Editor'])
        # reviewer 2
        self.assertEqual(manuscript.reviewers[1].name, 'Carl Bergstrom')
        self.assertEqual(manuscript.reviewers[1].orcid, None)
        self.assertEqual(manuscript.reviewers[1].title, '')
        self.assertEqual(manuscript.reviewers[1].person_id, '1046')
        self.assertEqual(manuscript.reviewers[1].roles, ['Reviewing Editor'])

    def test_manuscript_populate_from_row_none(self):
        """"empty row data"""
        manuscript = bigquery.Manuscript()
        self.assertIsNone(manuscript.populate_from_row(None))


class TestReviewer(unittest.TestCase):

    def test_reviewer_populate_from_dict_none(self):
        """"empty row data"""
        reviewer = bigquery.Reviewer()
        self.assertIsNone(reviewer.populate_from_dict(None))
