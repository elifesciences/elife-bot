# coding=utf-8

import os
from datetime import datetime
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import bigquery, utils
import activity.activity_FindFuturePreprints as activity_module
from activity.activity_FindFuturePreprints import (
    activity_FindFuturePreprints as activity_class,
)
from tests import bigquery_preprint_test_data
from tests.activity import settings_mock, test_activity_data
from tests.classes_mock import (
    FakeBigQueryClient,
    FakeBigQueryRowIterator,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeStorageContext,
)


class TestFindFuturePreprints(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_class(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch("provider.outbox_provider.storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(bigquery, "get_client")
    def test_do_activity(
        self,
        fake_bigquery_get_client,
        fake_get_current_datetime,
        fake_outbox_storage_context,
    ):
        "test activity success"
        directory = TempDirectory()

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        fake_get_current_datetime.return_value = datetime.strptime(
            "2025-11-03 +0000", "%Y-%m-%d %z"
        )

        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )

        expected_result = activity_class.ACTIVITY_SUCCESS

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertTrue(
            "FindFuturePreprints, found 2 future preprints"
            in self.activity.logger.loginfo
        )
        outbox_folder_path = os.path.join(
            directory.path, "crossref_pending_publication", "outbox"
        )
        outbox_file_list = sorted(os.listdir(outbox_folder_path))
        # assert outbox folder list
        self.assertEqual(
            outbox_file_list,
            ["elife-preprint-87445-v2.xml", "elife-preprint-92362-v1.xml"],
        )
        # assert XML output contents
        xml_string = None
        with open(
            os.path.join(outbox_folder_path, "elife-preprint-87445-v2.xml"),
            "r",
            encoding="utf-8",
        ) as open_file:
            xml_string = open_file.read()
        self.assertTrue(
            (
                '<article xmlns:mml="http://www.w3.org/1998/Math/MathML"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' article-type="research-article" dtd-version="1.1d3">'
            )
            in xml_string
        )
        self.assertTrue(
            '<issn publication-format="electronic">2050-084X</issn>' in xml_string
        )
        self.assertTrue(
            (
                '<article-id pub-id-type="doi"'
                ' specific-use="version">10.7554/eLife.87445.2</article-id>'
            )
            in xml_string
        )
        self.assertTrue(
            "<article-title>Title to be confirmed</article-title>" in xml_string
        )
        self.assertTrue("<elocation-id>RP87445</elocation-id>" in xml_string)
        self.assertTrue(
            (
                "<history>\n"
                '<date date-type="accepted">\n'
                "<day>03</day>\n"
                "<month>11</month>\n"
                "<year>2025</year>\n"
                "</date>\n"
                "</history>\n"
            )
            in xml_string
        )

    @patch.object(activity_module, "generate_preprint_xml_string")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(utils, "get_current_datetime")
    @patch.object(bigquery, "get_client")
    def test_do_activity_exception(
        self,
        fake_bigquery_get_client,
        fake_get_current_datetime,
        fake_outbox_storage_context,
        fake_generate,
    ):
        "test an exception raised generating XML string"
        directory = TempDirectory()

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        fake_get_current_datetime.return_value = datetime.strptime(
            "2025-11-03 +0000", "%Y-%m-%d %z"
        )

        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )

        exception_message = "An exception"
        fake_generate.side_effect = Exception(exception_message)

        expected_result = activity_class.ACTIVITY_SUCCESS

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "FindFuturePreprints, exception raised generating an XML string for"
                " version_doi 10.7554/eLife.87445.2: %s" % exception_message
            ),
        )


class TestGetFuturePreprintData(unittest.TestCase):
    "tests for get_future_preprint_data()"

    def setUp(self):
        self.caller_name = "FindFuturePreprints"
        self.logger = FakeLogger()

    @patch.object(bigquery, "get_client")
    def test_get_future_preprint_data(self, fake_bigquery_get_client):
        "test getting future preprint data from BigQuery"
        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_preprint_test_data.PREPRINT_QUERY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client
        # invoke
        result = activity_module.get_future_preprint_data(
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertIsNotNone(result)

    @patch.object(bigquery, "future_preprint_article_result")
    @patch.object(bigquery, "get_client")
    def test_exception(self, fake_bigquery_get_client, fake_get_data):
        "test exception raised when getting future preprints from BigQuery"
        client = FakeBigQueryClient([])
        fake_bigquery_get_client.return_value = client
        exception_message = "An exception"
        fake_get_data.side_effect = Exception(exception_message)
        # invoke
        activity_module.get_future_preprint_data(
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertEqual(
            ("%s, exception getting a list of future preprints" " from BigQuery: %s")
            % (self.caller_name, exception_message),
            self.logger.logexception,
        )
