import unittest
from mock import patch
from ddt import ddt, data
from provider.article import article
import activity.activity_PubRouterDeposit as activity_module
from activity.activity_PubRouterDeposit import activity_PubRouterDeposit
from tests.classes_mock import FakeSWFClient, FakeSMTPServer
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeKey, FakeLogger, FakeStorageContext
from tests.activity import settings_mock, test_activity_data


ARCHIVE_ZIP_BUCKET_S3_KEYS = [
    {
        "name": "elife-00013-vor-v1-20121015000000.zip",
        "last_modified": "2016-02-05T09:04:11.000Z",
    },
    {
        "name": "elife-09169-vor-v1-20150608000000.zip",
        "last_modified": "2020-02-05T09:04:11.000Z",
    },
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
    @patch("boto3.client")
    @patch.object(activity_PubRouterDeposit, "get_archive_bucket_s3_keys")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(article, "was_ever_published")
    def test_do_activity(
        self,
        fake_was_ever_published,
        fake_storage_context,
        fake_archive_bucket_s3_keys,
        fake_client,
        fake_article_versions,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.pubrouterdeposit.get_tmp_dir()
        )
        activity_data = {"data": {"workflow": "HEFCE"}}
        fake_was_ever_published.return_value = None
        fake_storage_context.return_value = FakeStorageContext(
            "tests/test_data/", ["elife00013.xml", "elife09169.xml"]
        )
        fake_archive_bucket_s3_keys.return_value = ARCHIVE_ZIP_BUCKET_S3_KEYS
        fake_client.return_value = FakeSWFClient()
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.article_versions")
    @patch("boto3.client")
    @patch.object(activity_PubRouterDeposit, "get_archive_bucket_s3_keys")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(article, "was_ever_published")
    def test_do_activity_not_published(
        self,
        fake_was_ever_published,
        fake_storage_context,
        fake_archive_bucket_s3_keys,
        fake_client,
        fake_article_versions,
        fake_email_smtp_connect,
    ):
        "test not_published logic by mocking Lax does not have version data"
        tmp_dir = self.pubrouterdeposit.get_tmp_dir()
        fake_email_smtp_connect.return_value = FakeSMTPServer(tmp_dir)
        activity_data = {"data": {"workflow": "HEFCE"}}
        fake_was_ever_published.return_value = None
        fake_storage_context.return_value = FakeStorageContext(
            "tests/test_data/", ["elife00013.xml", "elife09169.xml"]
        )
        fake_archive_bucket_s3_keys.return_value = ARCHIVE_ZIP_BUCKET_S3_KEYS
        fake_client.return_value = FakeSWFClient()
        fake_article_versions.return_value = (
            200,
            [{}],
        )
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)
        self.assertTrue(
            "Parsed https://doi.org/10.7554/eLife.09169"
            in self.pubrouterdeposit.admin_email_content
        )
        self.assertTrue(
            "Parsed https://doi.org/10.7554/eLife.00013"
            in self.pubrouterdeposit.admin_email_content
        )
        self.assertTrue(
            "Removing because it is not published 10.7554/eLife.09169"
            in self.pubrouterdeposit.admin_email_content
        )
        self.assertTrue(
            "Removing because it is not published 10.7554/eLife.00013"
            in self.pubrouterdeposit.admin_email_content
        )
        self.assertTrue(
            (
                (
                    "DOI 10.7554/eLife.09169, PubRouterDeposit to move file "
                    "%s/elife09169.xml to the not_published folder"
                )
                % tmp_dir
            )
            in self.pubrouterdeposit.admin_email_content
        )
        self.assertTrue(
            (
                (
                    "DOI 10.7554/eLife.00013, PubRouterDeposit to move file "
                    "%s/elife00013.xml to the not_published folder"
                )
                % tmp_dir
            )
            in self.pubrouterdeposit.admin_email_content
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @patch("boto3.client")
    @patch.object(activity_PubRouterDeposit, "get_archive_bucket_s3_keys")
    @patch("provider.outbox_provider.storage_context")
    @data("PMC")
    def test_do_activity_pmc(
        self,
        workflow_name,
        fake_storage_context,
        fake_archive_bucket_s3_keys,
        fake_client,
        fake_article_versions,
        fake_was_ever_poa,
        fake_email_smtp_connect,
    ):
        "test for PMC runs which start a different workflow"
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.pubrouterdeposit.get_tmp_dir()
        )
        activity_data = {"data": {"workflow": workflow_name}}
        fake_storage_context.return_value = FakeStorageContext(
            "tests/test_data/", ["elife00013.xml"]
        )
        fake_archive_bucket_s3_keys.return_value = ARCHIVE_ZIP_BUCKET_S3_KEYS
        fake_was_ever_poa.return_value = False
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        fake_client.return_value = FakeSWFClient()
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @patch.object(activity_module, "storage_context")
    def test_get_archive_bucket_s3_keys(self, fake_storage_context):
        # create mock Key object with name and last_modified value
        zip_file_name = "elife-00353-vor-v1-20121213000000.zip"
        last_modified = "2019-05-31T00:00:00.000Z"
        resources = [
            FakeKey(name=zip_file_name, last_modified="2019-05-31T00:00:00.000Z")
        ]
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder, resources
        )
        expected = [{"name": zip_file_name, "last_modified": last_modified}]
        s3_keys = self.pubrouterdeposit.get_archive_bucket_s3_keys()
        self.assertEqual(s3_keys, expected)

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


class TestApproveForOaSwitchboard(unittest.TestCase):
    def test_approve_for_oa_switchboard_true(self):
        article_object = article()
        article_object.parse_article_file(
            "tests/files_source/oaswitchboard/outbox/elife-70357-v2.xml"
        )
        self.assertEqual(
            activity_module.approve_for_oa_switchboard(article_object), True
        )

    def test_approve_for_oa_switchboard_false(self):
        article_object = article()
        article_object.parse_article_file(
            "tests/files_source/oaswitchboard/outbox/elife-00353-v1.xml"
        )
        self.assertEqual(
            activity_module.approve_for_oa_switchboard(article_object), False
        )
