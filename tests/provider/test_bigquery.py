import unittest
import datetime
from mock import patch
from google.oauth2.service_account import Credentials
from google.cloud.bigquery import Client
from google.cloud.bigquery.table import Row
from google.cloud._helpers import _UTC
from provider import bigquery
import tests.settings_mock as settings_mock


ARTICLE_RESULT_15747 = Row(
    (
        (
            '15747', '10.7554/eLife.15747',
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=_UTC()),
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=_UTC()),
            [
                {
                    'Name': 'Ian Baldwin',
                    'ORCID': None,
                    'Title': 'Dr.',
                    'Person_ID': '1013',
                    'Roles': ['Senior Editor']
                },
                {
                    'Name': 'Carl Bergstrom',
                    'ORCID': None,
                    'Title': '',
                    'Person_ID': '1046',
                    'Roles': ['Reviewing Editor']
                }]
            )
        ),
    {
        'Manuscript_ID': 0,
        'DOI': 1,
        'QC_Complete_Timestamp': 2,
        'Decision_Sent_Timestamp': 3,
        'Reviewers_And_Editors': 4
        }
    )


class FakeBigQueryClient():

    def __init__(self, result):
        self.result = result

    def query(self, query):
        return FakeQueryJob(self.result)


class FakeQueryJob():

    def __init__(self, result_return):
        self.result_return = result_return

    def result(self):
        return self.result_return


class FakeRowIterator():

    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        for row in self.rows:
            yield row


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
        rows = FakeRowIterator([ARTICLE_RESULT_15747])
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
        self.assertEqual(bigquery.get_review_date(None, None), "1970-01-02")
