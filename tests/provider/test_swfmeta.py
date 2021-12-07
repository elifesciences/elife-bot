import unittest
import os
import json
from provider.swfmeta import SWFMeta
import tests.settings_mock as settings_mock
from testfixtures import tempdir
from testfixtures import TempDirectory
from mock import patch, MagicMock


class FakeSWFConnection:
    def __init__(self):
        # infos is JSON format infos in SWF format for workflow executions
        self.infos = []
        self.infos_counter = 0

    def connect(self):
        pass

    def add_infos(self, infos):
        "add an infos, to allow it to return more than one infos in succession"
        self.infos.append(infos)

    def list_open_workflow_executions(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        oldest_date=None,
        latest_date=None,
        maximum_page_size=None,
        next_page_token=None,
    ):
        """
        return the infos for testing, when testing the next_page_token and
        mocking the return values the final infos value needs not have a
        nextPageToken otherwise it will loop forever in some swfmeta functions
        """
        if len(self.infos) > 1:
            return_infos = self.infos[self.infos_counter]
            if self.infos_counter + 1 < len(self.infos):
                self.infos_counter = self.infos_counter + 1
            else:
                self.infos_counter = 0
            return return_infos
        else:
            # reset the counter self.infos_counter then return
            self.infos_counter = 0
            return self.infos[self.infos_counter]

    def list_closed_workflow_executions(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        start_oldest_date=None,
        start_latest_date=None,
        close_status=None,
        maximum_page_size=None,
        next_page_token=None,
    ):
        "for testing piggy-back list_open_workflow_executions to return infos"
        return self.list_open_workflow_executions()


class TestProviderSWFMeta(unittest.TestCase):
    def setUp(self):
        self.swfmeta = SWFMeta(settings_mock)

    def test_is_workflow_open(self):
        "test whether a workflow is open on a test fixture JSON example open workflow executions"
        with open("tests/test_data/open_workflow_executions.json", "r") as json_file:
            infos = json.loads(json_file.read())
            is_open = self.swfmeta.is_workflow_open(
                infos=infos, workflow_name="DepositCrossref"
            )
            self.assertTrue(is_open)
        # example where executionInfos list would be empty
        infos = json.loads('{"executionInfos": []}')
        is_open = self.swfmeta.is_workflow_open(
            infos=infos, workflow_name="DepositCrossref"
        )
        self.assertFalse(is_open)

    def test_get_last_completed(self):
        "test last completed workflow with a test fixture of closed workflow executions"
        expected_timestamp = 1371047538.231
        with open(
            "tests/test_data/completed_workflow_executions.json", "r"
        ) as json_file:
            infos = json.loads(json_file.read())
            latest_timestamp = (
                self.swfmeta.get_last_completed_workflow_execution_startTimestamp(
                    infos=infos, workflow_name="DepositCrossref"
                )
            )
            self.assertEqual(latest_timestamp, expected_timestamp)

    @patch("provider.swfmeta.SWFMeta.connect")
    def test_get_open_workflow_executionInfos(self, mock_connect):
        "test getting open workflow executions"
        # prepare some test data first
        base_infos = None
        next_page_token_infos = None
        with open("tests/test_data/open_workflow_executions.json", "r") as json_file:
            infos_data = json_file.read()
            base_infos = json.loads(infos_data)
            # also create the example with a nextPageToken
            next_page_token_infos = json.loads(infos_data)
            next_page_token_infos["nextPageToken"] = "a_next_page_token_for_testing"

        # first test is without a next_page_token
        mock_connect = FakeSWFConnection()
        mock_connect.add_infos(base_infos)
        self.swfmeta.conn = mock_connect
        infos = self.swfmeta.get_open_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)

        # second test is to add the data that has a nextPageToken to test pagination
        mock_connect = FakeSWFConnection()
        mock_connect.add_infos(next_page_token_infos)
        mock_connect.add_infos(base_infos)
        self.swfmeta.conn = mock_connect
        infos = self.swfmeta.get_open_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)

    @patch("provider.swfmeta.SWFMeta.connect")
    def test_get_closed_workflow_executionInfos(self, mock_connect):
        "test getting closed workflow executions"
        # prepare some test data first
        base_infos = None
        next_page_token_infos = None
        with open(
            "tests/test_data/completed_workflow_executions.json", "r"
        ) as json_file:
            infos_data = json_file.read()
            base_infos = json.loads(infos_data)
            # also create the example with a nextPageToken
            next_page_token_infos = json.loads(infos_data)
            next_page_token_infos["nextPageToken"] = "a_next_page_token_for_testing"

        # first test is without a next_page_token
        mock_connect = FakeSWFConnection()
        mock_connect.add_infos(base_infos)
        self.swfmeta.conn = mock_connect
        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 43)

        # second test is without a next_page_token and a close_status
        mock_connect = FakeSWFConnection()
        mock_connect.add_infos(base_infos)
        self.swfmeta.conn = mock_connect
        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref", close_status="COMPLETED"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 25)

        # third test is to add the data that has a nextPageToken to test pagination
        mock_connect = FakeSWFConnection()
        mock_connect.add_infos(next_page_token_infos)
        mock_connect.add_infos(base_infos)
        self.swfmeta.conn = mock_connect
        infos = self.swfmeta.get_closed_workflow_executionInfos(
            workflow_name="DepositCrossref", close_status="TERMINATED"
        )
        self.assertIsNotNone(infos)
        self.assertEqual(len(infos.get("executionInfos")), 15)


if __name__ == "__main__":
    unittest.main()
