import unittest
import json
from provider.simpleDB import SimpleDB
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
        self.assertEqual(self.provider.get_domain_name('EmailQueue'), 'EmailQueue_test')

    @data(
        {
            "file_data_type": None,
            "doi_id": None,
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name is not null order by name asc")
        },
        {
            "file_data_type": "xml",
            "doi_id": None,
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.xml%' order by name asc")
        },
        {
            "file_data_type": "figures",
            "doi_id": None,
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%figures%' order by name asc")
        },
        {
            "file_data_type": None,
            "doi_id": "00013",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '00013/%' order by name asc")
        },
        {
            "file_data_type": None,
            "doi_id": None,
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and last_modified_timestamp > '1356998400'" +
                " and name is not null order by name asc")
        },
        {
            "file_data_type": "xml",
            "doi_id": "00013",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.xml%' and name like '00013/%' order by name asc")
        },
        {
            "file_data_type": "svg",
            "doi_id": "00013",
            "last_updated_since": None,
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.svg%' and name like '00013/%' order by name asc")
        },
        {
            "file_data_type": None,
            "doi_id": "00013",
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '00013/%' and last_modified_timestamp > '1356998400'" +
                " order by name asc")
        },
        {
            "file_data_type": "xml",
            "doi_id": None,
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.xml%' and last_modified_timestamp > '1356998400'" +
                " order by name asc")
        },
        {
            "file_data_type": "xml",
            "doi_id": "00013",
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.xml%' and name like '00013/%'" +
                " and last_modified_timestamp > '1356998400' order by name asc")
        },
        {
            "file_data_type": "svg",
            "doi_id": "00013",
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%.svg%' and name like '00013/%'" +
                " and last_modified_timestamp > '1356998400' order by name asc")
        },
        {
            "file_data_type": "figures",
            "doi_id": "00778",
            "last_updated_since": "2013-01-01T00:00:00.000Z",
            "expected_query": (
                "select * from S3FileLog_dev where bucket_name = 'elife-articles'" +
                " and name like '%figures%' and name like '00778/%'" +
                " and last_modified_timestamp > '1356998400' order by name asc")
        },
    )
    def test_elife_get_article_s3_query(self, test_data):
        query = self.provider.elife_get_article_S3_query(
            date_format="%Y-%m-%dT%H:%M:%S.000Z",
            domain_name="S3FileLog_dev",
            file_data_types=["xml", "pdf", "img", "suppl", "video", "svg", "figures"],
            bucket_name="elife-articles",
            file_data_type=test_data.get("file_data_type"),
            doi_id=test_data.get("doi_id"),
            last_updated_since=test_data.get("last_updated_since")
        )
        self.assertEqual(query, test_data.get("expected_query"))

    @data(
        {
            "filename": "tests/test_data/provider.simpleDB.elife_articles.latest01.json",
            "expected_count": 20
        },
        {
            "filename": "tests/test_data/provider.simpleDB.elife_articles.latest02.json",
            "expected_count": 4
        }
    )
    @unpack
    def test_elife_filter(self, filename, expected_count):
        file_data_types = ["xml", "pdf", "img", "suppl", "video", "svg"]
        with open(filename, 'rb') as open_file:
            item_list = json.loads(open_file.read())
        filtered_item_list = self.provider.elife_filter_latest_article_S3_file_items(
            item_list, file_data_types)
        self.assertEqual(len(filtered_item_list), expected_count)

    def test_elife_filter_detail_list_one(self):
        filename = "tests/test_data/provider.simpleDB.elife_articles.latest01.json"
        file_data_types = ["xml", "pdf", "img", "suppl", "video", "svg"]
        with open(filename, 'rb') as open_file:
            item_list = json.loads(open_file.read())
        filtered_item_list = self.provider.elife_filter_latest_article_S3_file_items(
            item_list, file_data_types)
        self.assertEqual(filtered_item_list[10]["name"], "00005/elife_2012_00005.video.zip")
        self.assertEqual(filtered_item_list[3]["name"], "00003/elife_2012_00003.xml.zip")
        self.assertEqual(filtered_item_list[8]["name"], "00005/elife_2012_00005.pdf.zip")
        self.assertEqual(filtered_item_list[8]["last_modified_timestamp"], "1359244876")

    def test_elife_filter_detail_list_two(self):
        filename = "tests/test_data/provider.simpleDB.elife_articles.latest02.json"
        file_data_types = ["xml", "pdf", "img", "suppl", "video", "svg"]
        with open(filename, 'rb') as open_file:
            item_list = json.loads(open_file.read())
        filtered_item_list = self.provider.elife_filter_latest_article_S3_file_items(
            item_list, file_data_types)
        self.assertEqual(filtered_item_list[0]["name"], "00003/elife_2012_00003.xml.zip")
        self.assertEqual(filtered_item_list[3]["name"], "00048/elife_2012_00048.xml.r6.zip")
        self.assertEqual(filtered_item_list[1]["name"], "00005/elife00005.xml")
        self.assertEqual(filtered_item_list[1]["last_modified_timestamp"], "1359244983")

    @data(
        {
            "sort_by": None,
            "query_type": None,
            "limit": None,
            "sent_status": None,
            "email_type": None,
            "doi_id": None,
            "date_scheduled_before": None,
            "date_sent_before": None,
            "recipient_email": None,
            "expected_query": "select * from EmailQueue_dev where sent_status is null"
        },
        {
            "sort_by": "date_added_timestamp",
            "query_type": "items",
            "limit": None,
            "sent_status": None,
            "email_type": None,
            "doi_id": None,
            "date_scheduled_before": None,
            "date_sent_before": None,
            "recipient_email": None,
            "expected_query": (
                "select * from EmailQueue_dev where sent_status is null" +
                " and date_added_timestamp is not null order by date_added_timestamp asc")
        },
        {
            "sort_by": None,
            "query_type": "count",
            "limit": None,
            "sent_status": None,
            "email_type": None,
            "doi_id": None,
            "date_scheduled_before": None,
            "date_sent_before": None,
            "recipient_email": None,
            "expected_query": "select count(*) from EmailQueue_dev where sent_status is null"
        },
        {
            "sort_by": None,
            "query_type": "count",
            "limit": None,
            "sent_status": None,
            "email_type": None,
            "doi_id": None,
            "date_scheduled_before": "1970-01-01T00:00:01.000Z",
            "date_sent_before": None,
            "recipient_email": None,
            "expected_query": (
                "select count(*) from EmailQueue_dev where sent_status is null" +
                " and date_scheduled_timestamp < '1'")
        },
    )
    def test_elife_get_email_queue_query(self, test_data):
        query = self.provider.elife_get_email_queue_query(
            date_format="%Y-%m-%dT%H:%M:%S.000Z",
            domain_name="EmailQueue_dev",
            query_type=test_data.get("query_type"),
            sort_by=test_data.get("sort_by"),
            limit=test_data.get("limit"),
            sent_status=test_data.get("sent_status"),
            email_type=test_data.get("email_type"),
            doi_id=test_data.get("doi_id"),
            date_scheduled_before=test_data.get("date_scheduled_before"),
            date_sent_before=test_data.get("date_sent_before"),
            recipient_email=test_data.get("recipient_email"),
        )
        self.assertEqual(query, test_data.get("expected_query"))

    @data(
        {
            "timestamp": 1,
            "doi_id": None,
            "email_type": None,
            "recipient_email": None,
            "expected_unique_item_name": "1",
        },
        {
            "timestamp": 1,
            "doi_id": "00003",
            "email_type": "example",
            "recipient_email": "elife@example.org",
            "expected_unique_item_name": "1__00003__example__elife@example.org",
        },
    )
    def test_elife_get_unique_email_queue_item_name(self, test_data):
        unique_item_name = self.provider.elife_get_unique_email_queue_item_name(
            domain_name="EmailQueue_dev",
            check_is_unique=None,
            timestamp=test_data.get("timestamp"),
            doi_id=test_data.get("doi_id"),
            email_type=test_data.get("email_type"),
            recipient_email=test_data.get("recipient_email"),
        )
        self.assertEqual(unique_item_name, test_data.get("expected_unique_item_name"))

    def test_elife_add_email_to_email_queue(self):
        email_type = "test"
        recipient_email = "test@example.org"
        sender_email = "test@example.org"
        result = self.provider.elife_add_email_to_email_queue(
            recipient_email=recipient_email,
            sender_email=sender_email,
            email_type=email_type,
            date_scheduled_timestamp=0,
            add=False)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("email_type"), email_type)
        self.assertEqual(result.get("recipient_email"), recipient_email)
        self.assertEqual(result.get("sender_email"), sender_email)

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
            date_format="%Y-%m-%dT%H:%M:%S.000Z",
            domain_name=domain_name,
            bucket_name=bucket_name,
            last_updated_since=last_updated_since)
        self.assertEqual(query, expected_query)


if __name__ == '__main__':
    unittest.main()
