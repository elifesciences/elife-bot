import unittest
from collections import OrderedDict
import copy
import datetime
import json
from mock import patch
from provider.swfmeta import query_kwargs, SWFMeta
from tests.classes_mock import FakeSWFClient
from tests import read_fixture, settings_mock


class TestQueryKwargs(unittest.TestCase):
    def test_query_kwargs_all(self):
        "test all keyword arguments for test coverage"
        kwargs = query_kwargs(
            domain="domain",
            workflow_id="workflow_id",
            workflow_name="workflow_name",
            workflow_version="workflow_version",
            start_oldest_date=datetime.datetime(2013, 6, 12, 7, 34, 14, 235000),
            start_latest_date=datetime.datetime(2013, 6, 12, 7, 34, 14, 235001),
            close_status="close_status",
            maximum_page_size="maximum_page_size",
        )
        expected = OrderedDict(
            [
                ("domain", "domain"),
                (
                    "startTimeFilter",
                    {
                        "oldestDate": datetime.datetime(2013, 6, 12, 7, 34, 14, 235000),
                        "latestDate": datetime.datetime(2013, 6, 12, 7, 34, 14, 235001),
                    },
                ),
                ("executionFilter", {"workflowId": "workflow_id"}),
                (
                    "typeFilter",
                    {"name": "workflow_name", "version": "workflow_version"},
                ),
                ("maximumPageSize", "maximum_page_size"),
            ]
        )
        self.assertEqual(kwargs, expected)

    def test_query_kwargs_close_status(self):
        "test close_status without a workflow_name or workflow_id"
        kwargs = query_kwargs(
            close_status="close_status",
        )

        expected = OrderedDict(
            [("domain", None), ("closeStatusFilter", {"status": "close_status"})]
        )
        self.assertEqual(kwargs, expected)


class TestProviderSWFMeta(unittest.TestCase):
    def setUp(self):
        self.swfmeta = SWFMeta(settings_mock)
        self.empty_infos = json.loads('{"executionInfos": []}')
        # deepcopy these to avoid strange side-effects
        self.base_open_infos = copy.deepcopy(
            read_fixture("open_workflow_executions.py")
        )
        self.base_completed_infos = copy.deepcopy(
            read_fixture("completed_workflow_executions.py")
        )

    @patch("boto3.client")
    def test_is_workflow_open(self, fake_client):
        "test whether a workflow is open on a test fixture JSON example open workflow executions"
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_open_infos)
        fake_client.return_value = mock_swf_client
        is_open = self.swfmeta.is_workflow_open(workflow_name="DepositCrossref")
        self.assertTrue(is_open)

    @patch("boto3.client")
    def test_is_workflow_open_empty_list(self, fake_client):
        "test whether a workflow is open, example where executionInfos list would be empty"
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.empty_infos)
        fake_client.return_value = mock_swf_client
        is_open = self.swfmeta.is_workflow_open(workflow_name="DepositCrossref")
        self.assertFalse(is_open)

    @patch("boto3.client")
    def test_get_closed_workflow_execution_count(self, fake_client):
        "test counting of closed executions"
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_completed_infos)
        fake_client.return_value = mock_swf_client
        count = self.swfmeta.get_closed_workflow_execution_count(
            workflow_name="DepositCrossref"
        )
        self.assertEqual(count, 43)

    @patch("boto3.client")
    def test_get_last_completed(self, fake_client):
        "test last completed workflow with a test fixture of closed workflow executions"
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_completed_infos)
        fake_client.return_value = mock_swf_client
        expected_timestamp = 1371047538.231
        latest_timestamp = (
            self.swfmeta.get_last_completed_workflow_execution_startTimestamp(
                workflow_name="DepositCrossref"
            )
        )
        self.assertEqual(latest_timestamp, expected_timestamp)

    @patch("boto3.client")
    def test_get_open_workflow_execution_infos(self, fake_client):
        "test getting open workflow executions"
        # test without a next_page_token
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_open_infos)
        fake_client.return_value = mock_swf_client
        infos = self.swfmeta.get_open_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)

    @patch("boto3.client")
    def test_get_open_workflow_next_token(self, fake_client):
        "test getting open workflow executions"
        # add a nextPageToken
        next_page_token_infos = copy.deepcopy(self.base_open_infos)
        next_page_token_infos["nextPageToken"] = "a_next_page_token_for_testing"

        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(next_page_token_infos)
        mock_swf_client.add_infos(self.base_open_infos)
        fake_client.return_value = mock_swf_client

        infos = self.swfmeta.get_open_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos["executionInfos"]), 2)

    @patch("boto3.client")
    def test_get_closed_workflow_execution_infos(self, fake_client):
        "test getting closed workflow executions"
        # test without a next_page_token
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_completed_infos)
        fake_client.return_value = mock_swf_client

        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 43)

    @patch("boto3.client")
    def test_get_closed_workflow_by_close_status(self, fake_client):
        "test getting closed workflow executions"
        # test without a next_page_token
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(self.base_completed_infos)
        fake_client.return_value = mock_swf_client

        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref", close_status="COMPLETED"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 25)

    @patch("boto3.client")
    def test_get_closed_workflow_next_token(self, fake_client):
        # create infos data where executionInfos list is trucated to the first item only
        final_infos = copy.deepcopy(self.base_completed_infos)
        final_infos["executionInfos"] = final_infos["executionInfos"][:1]
        # also create the example with a nextPageToken
        next_page_token_infos = copy.deepcopy(self.base_completed_infos)
        next_page_token_infos["nextPageToken"] = "a_next_page_token_for_testing"

        # test with a nextPageToken to test pagination
        mock_swf_client = FakeSWFClient()
        mock_swf_client.add_infos(next_page_token_infos)
        mock_swf_client.add_infos(final_infos)
        fake_client.return_value = mock_swf_client

        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref", close_status="TERMINATED"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 15)
