import unittest
from provider import bigquery


class TestBigQueryProvider(unittest.TestCase):

    def test_get_review_date(self):
        self.assertEqual(bigquery.get_review_date(None, None), "1970-01-02")
