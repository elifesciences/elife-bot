import unittest
import datetime
from mock import patch
from ddt import ddt, data, unpack
from testfixtures import TempDirectory
from provider import yaml_provider
from provider.article import article
import activity.activity_PubRouterDeposit as activity_module
from activity.activity_PubRouterDeposit import activity_PubRouterDeposit
from tests.classes_mock import FakeSWFClient, FakeSMTPServer
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeStorageContext,
    FakeSQSClient,
    FakeSQSQueue,
)
from tests.activity import helpers, settings_mock, test_activity_data


ARCHIVE_ZIP_BUCKET_S3_KEYS = [
    {
        "Key": "elife-00013-vor-v1-20121015000000.zip",
        "LastModified": datetime.datetime(2016, 2, 5, 9, 4, 11),
    },
    {
        "Key": "elife-09169-vor-v1-20150608000000.zip",
        "LastModified": datetime.datetime(2020, 2, 5, 9, 4, 11),
    },
]


@ddt
class TestPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.pubrouterdeposit.clean_tmp_dir()
        helpers.delete_files_in_folder(
            test_activity_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("boto3.client")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.article_versions")
    @patch("boto3.client")
    @patch.object(activity_module, "storage_context")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(article, "was_ever_published")
    def test_do_activity(
        self,
        fake_was_ever_published,
        fake_outbox_storage_context,
        fake_storage_context,
        fake_client,
        fake_article_versions,
        fake_email_smtp_connect,
        fake_sqs_client,
    ):
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        activity_data = {"data": {"workflow": "HEFCE"}}
        fake_was_ever_published.return_value = None
        resources = helpers.populate_storage(
            from_dir="tests/test_data/",
            to_dir=directory.path,
            filenames=["elife00013.xml", "elife09169.xml"],
            sub_dir="pub_router/outbox",
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder,
            ARCHIVE_ZIP_BUCKET_S3_KEYS,
        )
        fake_client.return_value = FakeSWFClient()
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        # do the activity
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.lax_provider.article_versions")
    @patch("boto3.client")
    @patch.object(activity_module, "storage_context")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(article, "was_ever_published")
    def test_do_activity_not_published(
        self,
        fake_was_ever_published,
        fake_outbox_storage_context,
        fake_storage_context,
        fake_client,
        fake_article_versions,
        fake_email_smtp_connect,
    ):
        "test not_published logic by mocking Lax does not have version data"
        directory = TempDirectory()
        tmp_dir = self.pubrouterdeposit.get_tmp_dir()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        activity_data = {"data": {"workflow": "HEFCE"}}
        fake_was_ever_published.return_value = None
        resources = helpers.populate_storage(
            from_dir="tests/test_data/",
            to_dir=directory.path,
            filenames=["elife00013.xml", "elife09169.xml"],
            sub_dir="pub_router/outbox",
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder,
            ARCHIVE_ZIP_BUCKET_S3_KEYS,
        )
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
    @patch.object(activity_module, "storage_context")
    @patch("provider.outbox_provider.storage_context")
    @data("PMC")
    def test_do_activity_pmc(
        self,
        workflow_name,
        fake_outbox_storage_context,
        fake_storage_context,
        fake_client,
        fake_article_versions,
        fake_was_ever_poa,
        fake_email_smtp_connect,
    ):
        "test for PMC runs which start a different workflow"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        activity_data = {"data": {"workflow": workflow_name}}
        resources = helpers.populate_storage(
            from_dir="tests/test_data/",
            to_dir=directory.path,
            filenames=["elife00013.xml"],
            sub_dir="pmc/outbox",
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder,
            ARCHIVE_ZIP_BUCKET_S3_KEYS,
        )
        fake_was_ever_poa.return_value = False
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        fake_client.return_value = FakeSWFClient()
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_PubRouterDeposit, "start_pmc_deposit_workflow")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @patch.object(activity_module, "storage_context")
    @patch("provider.outbox_provider.storage_context")
    @data("PMC")
    def test_do_activity_pmc_starter_failure(
        self,
        workflow_name,
        fake_outbox_storage_context,
        fake_storage_context,
        fake_article_versions,
        fake_was_ever_poa,
        fake_start,
        fake_email_smtp_connect,
    ):
        "test for the the PMC starter function returns False"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        activity_data = {"data": {"workflow": workflow_name}}
        resources = helpers.populate_storage(
            from_dir="tests/test_data/",
            to_dir=directory.path,
            filenames=["elife00013.xml"],
            sub_dir="pmc/outbox",
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder,
            ARCHIVE_ZIP_BUCKET_S3_KEYS,
        )
        fake_was_ever_poa.return_value = False
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        fake_start.return_value = False
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)
        self.assertTrue(
            "PubRouterDeposit PMC FAILED to start a workflow for article: 10.7554/eLife.00013"
            in self.pubrouterdeposit.logger.loginfo
        )


class TestStartFtpArticleWorkflow(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )
        self.pubrouterdeposit.workflow = "HEFCE"
        self.article = article()
        self.article.doi_id = "00666"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_start_ftp_article_workflow(self, fake_sqs_client):
        directory = TempDirectory()
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        result = self.pubrouterdeposit.start_ftp_article_workflow(self.article)
        self.assertEqual(result, True)

    @patch.object(FakeSQSClient, "send_message")
    @patch("boto3.client")
    def test_start_ftp_article_workflow_exception(self, fake_sqs_client, fake_send):
        directory = TempDirectory()
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        exception_message = "An exception"
        fake_send.side_effect = Exception(exception_message)
        result = self.pubrouterdeposit.start_ftp_article_workflow(self.article)
        self.assertEqual(result, False)
        self.assertEqual(
            self.pubrouterdeposit.logger.logexception,
            "PubRouterDeposit exception starting workflow FTPArticle_%s_%s: %s"
            % (self.pubrouterdeposit.workflow, self.article.doi_id, exception_message),
        )


class TestGetArchiveBucketS3Keys(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )

    @patch.object(activity_module, "storage_context")
    def test_get_archive_bucket_s3_keys(self, fake_storage_context):
        # create mock Key object with name and last_modified value
        zip_file_name = "elife-00353-vor-v1-20121213000000.zip"
        last_modified = "2019-05-31T00:00:00.000Z"
        resources = [
            {"Key": zip_file_name, "LastModified": datetime.datetime(2019, 5, 31)}
        ]
        fake_storage_context.return_value = FakeStorageContext(
            test_activity_data.ExpandArticle_files_source_folder, resources
        )
        expected = [{"name": zip_file_name, "last_modified": last_modified}]
        s3_keys = self.pubrouterdeposit.get_archive_bucket_s3_keys()
        self.assertEqual(s3_keys, expected)


class TestStartPmcDepositWorkflow(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )
        self.pubrouterdeposit.workflow = "PMCDeposit"
        self.article = article()
        self.article.doi_id = "00666"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_start_pmc_deposit_workflow(self, fake_sqs_client):
        directory = TempDirectory()
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        result = self.pubrouterdeposit.start_pmc_deposit_workflow(self.article, "", "")
        self.assertEqual(result, True)

    @patch.object(FakeSQSClient, "send_message")
    @patch("boto3.client")
    def test_start_pmc_deposit_workflow_exception(self, fake_sqs_client, fake_send):
        directory = TempDirectory()
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)
        exception_message = "An exception"
        fake_send.side_effect = Exception(exception_message)
        result = self.pubrouterdeposit.start_pmc_deposit_workflow(self.article, "", "")
        self.assertEqual(result, False)
        self.assertEqual(
            self.pubrouterdeposit.logger.logexception,
            "PubRouterDeposit exception starting workflow PMCDeposit_%s: %s"
            % (self.article.doi_id, exception_message),
        )


@ddt
class TestApproveArticles(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None
        )
        test_article = article()
        test_article.doi = "10.7554/eLife.00666"
        test_article.doi_id = "00666"
        test_article.article_type = "research-article"
        test_article.display_channel = ["Research Article"]
        test_article.is_poa = True
        self.articles = [test_article]
        self.rules = yaml_provider.load_config(settings_mock)

    @patch.object(activity_PubRouterDeposit, "get_latest_archive_zip_name")
    @patch("provider.article.article.was_ever_published")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @data(
        "Cengage",
        "CLOCKSS",
        "CNKI",
        "CNPIEC",
        "GoOA",
        "HEFCE",
        "OASwitchboard",
        "OVID",
        "PMC",
        "WoS",
        "Zendy",
    )
    def test_approve_articles(
        self,
        workflow_name,
        fake_article_versions,
        fake_was_ever_poa,
        fake_was_ever_published,
        fake_get_latest_archive_zip_name,
    ):
        fake_was_ever_poa.return_value = True
        fake_was_ever_published.return_value = False
        fake_get_latest_archive_zip_name.return_value = "test.zip"
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )

        expected_approved_article_dois = ["10.7554/eLife.00666"]
        expected_remove_doi_list = []
        approved_articles, remove_doi_list = self.pubrouterdeposit.approve_articles(
            self.articles, workflow_name, self.rules.get(workflow_name)
        )
        # self.assertTrue(False)
        approved_article_dois = [article.doi for article in approved_articles]
        self.assertEqual(approved_article_dois, expected_approved_article_dois)
        self.assertEqual(remove_doi_list, expected_remove_doi_list)

    @patch.object(activity_PubRouterDeposit, "get_latest_archive_zip_name")
    @patch("provider.article.article.was_ever_published")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @data(
        "OASwitchboard",
    )
    def test_approve_articles_oaswitchboard(
        self,
        workflow_name,
        fake_article_versions,
        fake_was_ever_poa,
        fake_was_ever_published,
        fake_get_latest_archive_zip_name,
    ):
        "test when OASwitchboard is not approved"
        fake_was_ever_poa.return_value = True
        fake_was_ever_published.return_value = False
        fake_get_latest_archive_zip_name.return_value = "test.zip"
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        # article test data that will not be sent to OASwitchboard
        self.articles[0].article_type = None
        expected_approved_article_dois = []
        expected_remove_doi_list = ["10.7554/eLife.00666"]
        approved_articles, remove_doi_list = self.pubrouterdeposit.approve_articles(
            self.articles, workflow_name, self.rules.get(workflow_name)
        )
        approved_article_dois = [article.doi for article in approved_articles]
        self.assertEqual(approved_article_dois, expected_approved_article_dois)
        self.assertEqual(remove_doi_list, expected_remove_doi_list)

    @patch.object(activity_PubRouterDeposit, "get_latest_archive_zip_name")
    @patch("provider.article.article.was_ever_published")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @data(
        "Cengage",
        "CNKI",
        "CNPIEC",
        "GoOA",
        "HEFCE",
        "OASwitchboard",
        "WoS",
    )
    def test_approve_articles_was_ever_published(
        self,
        workflow_name,
        fake_article_versions,
        fake_was_ever_poa,
        fake_was_ever_published,
        fake_get_latest_archive_zip_name,
    ):
        "test when was_ever_published is True for coverage adding the article to the remove list"

        fake_was_ever_poa.return_value = True
        fake_was_ever_published.return_value = True
        fake_get_latest_archive_zip_name.return_value = "test.zip"
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        expected_approved_article_dois = []
        expected_remove_doi_list = ["10.7554/eLife.00666"]
        approved_articles, remove_doi_list = self.pubrouterdeposit.approve_articles(
            self.articles, workflow_name, self.rules.get(workflow_name)
        )
        approved_article_dois = [article.doi for article in approved_articles]
        self.assertEqual(approved_article_dois, expected_approved_article_dois)
        self.assertEqual(remove_doi_list, expected_remove_doi_list)

    @patch.object(activity_PubRouterDeposit, "get_latest_archive_zip_name")
    @patch("provider.article.article.was_ever_published")
    @patch("provider.lax_provider.was_ever_poa")
    @patch("provider.lax_provider.article_versions")
    @data(
        "Cengage",
        "CLOCKSS",
        "CNKI",
        "CNPIEC",
        "GoOA",
        "HEFCE",
        "OASwitchboard",
        "PMC",
        "WoS",
    )
    def test_approve_articles_archive_zip_does_not_exist(
        self,
        workflow_name,
        fake_article_versions,
        fake_was_ever_poa,
        fake_was_ever_published,
        fake_get_latest_archive_zip_name,
    ):
        "test when was_ever_published is False for coverage"
        fake_was_ever_poa.return_value = True
        fake_was_ever_published.return_value = False
        fake_get_latest_archive_zip_name.return_value = None
        fake_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        # article test data that will not be sent to OASwitchboard
        self.articles[0].article_type = None
        expected_approved_article_dois = []
        expected_remove_doi_list = ["10.7554/eLife.00666"]
        approved_articles, remove_doi_list = self.pubrouterdeposit.approve_articles(
            self.articles, workflow_name, self.rules.get(workflow_name)
        )
        approved_article_dois = [article.doi for article in approved_articles]
        self.assertEqual(approved_article_dois, expected_approved_article_dois)
        self.assertEqual(remove_doi_list, expected_remove_doi_list)


@ddt
class TestGetFriendlyEmailRecipients(unittest.TestCase):
    @unpack
    @data(
        {"workflow": "HEFCE", "settings_name": "HEFCE_EMAIL"},
        {"workflow": "Cengage", "settings_name": "CENGAGE_EMAIL"},
        {"workflow": "GoOA", "settings_name": "GOOA_EMAIL"},
        {"workflow": "CNPIEC", "settings_name": "CNPIEC_EMAIL"},
        {"workflow": "CNKI", "settings_name": "CNKI_EMAIL"},
        {"workflow": "CLOCKSS", "settings_name": "CLOCKSS_EMAIL"},
        {"workflow": "OVID", "settings_name": "OVID_EMAIL"},
        {"workflow": "Zendy", "settings_name": "ZENDY_EMAIL"},
        {"workflow": "OASwitchboard", "settings_name": "OASWITCHBOARD_EMAIL"},
    )
    def test_workflow_specific_values(self, workflow, settings_name):
        "test functions that look at the workflow name"
        recipient_email_list = activity_module.get_friendly_email_recipients(
            settings_mock, workflow
        )
        settings_value = getattr(settings_mock, settings_name, None)
        # determine the expect value from the settings
        if isinstance(settings_value, list):
            expected = settings_value
        else:
            # return value for blank strings from the function is an empty list
            expected = [settings_value] if settings_value else []
        # test assertion
        self.assertEqual(recipient_email_list, expected)

    def test_workflow_does_not_exist(self):
        "test functions that look at the workflow name"
        workflow = "foo"
        expected = []
        self.assertEqual(
            activity_module.get_friendly_email_recipients(settings_mock, workflow),
            expected,
        )

    def test_recipients_string(self):
        "test when the recipients is just a string and not a list"

        class TestSettings:
            downstream_recipients_yaml = "tests/downstreamRecipients.yaml"
            HEFCE_EMAIL = "email@example.org"

        test_settings = TestSettings()
        self.assertIsNotNone(
            activity_module.get_friendly_email_recipients(test_settings, "HEFCE")
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
