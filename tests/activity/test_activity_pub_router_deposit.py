import unittest
import os
import shutil
from mock import patch
from ddt import ddt, data, unpack
from provider import s3lib
from provider.article import article
import activity.activity_PubRouterDeposit as activity_module
from activity.activity_PubRouterDeposit import activity_PubRouterDeposit
from tests.classes_mock import FakeSMTPServer
import tests.test_data as test_case_data
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


WORKFLOW_NAMES = [
    "HEFCE",
    "Cengage",
    "WoS",
    "GoOA",
    "CNPIEC",
    "CNKI",
    "CLOCKSS",
    "OVID",
    "Zendy",
]


@ddt
class TestPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        self.pubrouterdeposit.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.article_versions")
    @patch.object(activity_PubRouterDeposit, "start_ftp_article_workflow")
    @patch.object(activity_PubRouterDeposit, "does_source_zip_exist_from_s3")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(article, "was_ever_published")
    @patch.object(s3lib, "get_s3_keys_from_bucket")
    def test_do_activity(
        self,
        fake_get_s3_keys,
        fake_was_ever_published,
        fake_storage_context,
        fake_outbox_key_names,
        fake_zip_exists,
        fake_start,
        fake_article_versions,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.pubrouterdeposit.get_tmp_dir()
        )
        activity_data = {"data": {"workflow": "HEFCE"}}
        fake_was_ever_published.return_value = None
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        fake_outbox_key_names.return_value = ["elife00013.xml", "elife09169.xml"]
        fake_zip_exists.return_value = True
        fake_start.return_value = True
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @patch.object(activity_PubRouterDeposit, "start_pmc_deposit_workflow")
    @patch.object(activity_PubRouterDeposit, "archive_zip_file_name")
    @patch("provider.outbox_provider.get_outbox_s3_key_names")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(s3lib, "get_s3_keys_from_bucket")
    @data("PMC")
    def test_do_activity_pmc(
        self,
        workflow_name,
        fake_get_s3_keys,
        fake_storage_context,
        fake_outbox_key_names,
        fake_archive_zip_file_name,
        fake_start,
        fake_article_versions,
        fake_was_ever_poa,
        fake_email_smtp_connect,
    ):
        "test for PMC runs which start a different workflow"
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.pubrouterdeposit.get_tmp_dir()
        )
        activity_data = {"data": {"workflow": workflow_name}}
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        fake_outbox_key_names.return_value = ["elife00013.xml"]
        fake_archive_zip_file_name.return_value = "elife-01-00013.zip"
        fake_was_ever_poa.return_value = False
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        fake_start.return_value = True
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @data(
        "HEFCE",
        "Cengage",
        "GoOA",
        "WoS",
        "CNPIEC",
        "CNKI",
        "CLOCKSS",
    )
    def test_workflow_specific_values(self, workflow):
        "test functions that look at the workflow name"
        self.assertIsNotNone(
            self.pubrouterdeposit.get_friendly_email_recipients(workflow)
        )


class TestGetOutboxFolder(unittest.TestCase):
    def test_get_outbox_folder(self):
        for workflow in WORKFLOW_NAMES:
            self.assertIsNotNone(activity_module.get_outbox_folder(workflow))

    def test_get_outbox_folder_undefined(self):
        workflow = "foo"
        self.assertIsNone(activity_module.get_outbox_folder(workflow))


class TestGetPublishedFolder(unittest.TestCase):
    def test_get_published_folder(self):
        for workflow in WORKFLOW_NAMES:
            self.assertIsNotNone(activity_module.get_published_folder(workflow))

    def test_get_published_folder_undefined(self):
        workflow = "foo"
        self.assertIsNone(activity_module.get_published_folder(workflow))
