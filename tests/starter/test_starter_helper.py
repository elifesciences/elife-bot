import unittest
import json
from ddt import ddt, data, unpack
from mock import patch
from starter import starter_helper
from tests import test_data
from tests.classes_mock import FakeSWFClient
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger


EXAMPLE_WORKFLOW_NAME = "PostPerfectPublication"
EXAMPLE_WORKFLOW_ID = (
    lambda fe, version: "PostPerfectPublication_353." + version + "." + fe
)


@ddt
class TestStarterHelper(unittest.TestCase):
    @unpack
    @data(
        {"execution_data": test_data.data_published_lax, "execution": "lax"},
        {"execution_data": test_data.data_error_lax, "execution": "lax"},
        {"execution_data": test_data.data_published_website, "execution": "website"},
    )
    def test_set_workflow_information_lax(self, execution_data, execution):

        (
            workflow_id,
            workflow_name,
            workflow_version,
            child_policy,
            execution_start_to_close_timeout,
            workflow_input,
        ) = starter_helper.set_workflow_information(
            EXAMPLE_WORKFLOW_NAME,
            "1",
            None,
            execution_data,
            "%s.%s" % (execution_data.get("article_id"), execution_data.get("version")),
            execution,
        )

        self.assertEqual(
            EXAMPLE_WORKFLOW_ID(execution, execution_data.get("version")), workflow_id
        )
        self.assertEqual(EXAMPLE_WORKFLOW_NAME, workflow_name)
        self.assertEqual("1", workflow_version)
        self.assertIsNone(child_policy)
        self.assertEqual("1800", execution_start_to_close_timeout)
        self.assertEqual(json.dumps(execution_data), workflow_input)

    def test_get_starter_module(self):
        "for coverage successful starter module import"
        starter_name = "starter_PackagePOA"
        module_object = starter_helper.get_starter_module(starter_name, FakeLogger())
        self.assertIsNotNone(module_object)

    def test_get_starter_module_failure(self):
        "for coverage test failure"
        starter_name = "not_a_starter"
        module_object = starter_helper.get_starter_module(starter_name, FakeLogger())
        self.assertIsNone(module_object)

    def test_import_starter_module_failure(self):
        "for coverage test import failure"
        starter_name = "not_a_starter"
        return_value = starter_helper.import_starter_module(starter_name, FakeLogger())
        self.assertFalse(return_value)

    @patch("boto3.client")
    def test_start_ping_marker(self, fake_client):
        fake_logger = FakeLogger()
        fake_client.return_value = FakeSWFClient()
        starter_helper.start_ping_marker("workflow_id", settings_mock, fake_logger)
        self.assertEqual(fake_logger.logexception, "First logger exception")
