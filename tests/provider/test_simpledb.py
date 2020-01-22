import unittest
import json
from provider.simpleDB import SimpleDB
from provider import utils
import tests.settings_mock as settings_mock
from ddt import ddt, data, unpack


@ddt
class TestSimpleDB(unittest.TestCase):

    def setUp(self):
        self.provider = SimpleDB(settings_mock)

    @data(
        ('test', 'test'),
        ('123', '123'),
        ("O'Reilly", "O''Reilly")
    )
    @unpack
    def test_escape(self, value, expected):
        self.assertEqual(self.provider.escape(value), expected)

    def test_get_domain_name(self):
        self.assertEqual(self.provider.get_domain_name('S3File'), 'S3File_test')
        self.assertEqual(self.provider.get_domain_name('S3FileLog'), 'S3FileLog_test')

    @data(
        {
            "domain_name": "S3FileLog_dev",
            "bucket_name": "elife-ejp-poa-delivery-dev",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-ejp-poa-delivery-dev'" +
                " and last_modified_timestamp is not null order by last_modified_timestamp desc")
        },
        {
            "domain_name": "S3FileLog_dev",
            "bucket_name": "elife-ejp-poa-delivery-dev",
            "last_updated_since": "2014-04-20T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-ejp-poa-delivery-dev'" +
                " and last_modified_timestamp > '1397952000'" +
                " order by last_modified_timestamp desc")
        },
        {
            "domain_name": "S3FileLog",
            "bucket_name": "elife-production-final",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog where bucket_name = 'elife-production-final'" +
                " and last_modified_timestamp is not null order by last_modified_timestamp desc")
        },
        {
            "domain_name": "S3FileLog",
            "bucket_name": "elife-production-final",
            "last_updated_since": "2014-04-20T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog where bucket_name = 'elife-production-final'" +
                " and last_modified_timestamp > '1397952000'" +
                " order by last_modified_timestamp desc")
        },
        {
            "domain_name": "S3FileLog",
            "bucket_name": "elife-production-lens-jpg",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog where bucket_name = 'elife-production-lens-jpg'" +
                " and last_modified_timestamp is not null order by last_modified_timestamp desc")
        },
        {
            "domain_name": "S3FileLog",
            "bucket_name": "elife-production-lens-jpg",
            "last_updated_since": "2014-04-20T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog where bucket_name = 'elife-production-lens-jpg'" +
                " and last_modified_timestamp > '1397952000'" +
                " order by last_modified_timestamp desc")
        },
    )
    @unpack
    def test_elife_get_generic_delivery_s3_query(self, domain_name, bucket_name,
                                                 last_updated_since, expected_query):
        query = self.provider.elife_get_generic_delivery_S3_query(
            date_format=utils.DATE_TIME_FORMAT,
            domain_name=domain_name,
            bucket_name=bucket_name,
            last_updated_since=last_updated_since)
        self.assertEqual(query, expected_query)


if __name__ == '__main__':
    unittest.main()
