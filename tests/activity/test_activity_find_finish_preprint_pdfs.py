import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import preprint
import activity.activity_FindFinishPreprintPDFs as activity_module
from activity.activity_FindFinishPreprintPDFs import (
    activity_FindFinishPreprintPDFs as activity_class,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSQSClient,
    FakeSQSQueue,
    FakeStorageContext,
)
from tests.activity import settings_mock


def mock_preprint_pdf_url(url, caller_name, user_agent):
    if url.endswith("95901v1"):
        return "https://example.org/95901v1.pdf"
    raise RuntimeError


class TestFindFinishPreprintPDFs(unittest.TestCase):
    def setUp(self):
        self.activity = activity_class(settings_mock, FakeLogger(), None, None, None)
        self.activity_data = {}
        activity_module.API_SLEEP_SECONDS = 0

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    @patch("boto3.client")
    @patch.object(preprint, "get_preprint_pdf_url")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity(
        self,
        fake_outbox_storage_context,
        fake_get_preprint_pdf_url,
        fake_sqs_client,
    ):
        directory = TempDirectory()
        # populate the outbox folder
        outbox_file_names = [
            "finish_preprint/outbox/elife-preprint-95901-v1.xml",
            "finish_preprint/outbox/elife-preprint-84364-v2.xml",
            "finish_preprint/outbox/foo.xml",
        ]
        resources = []
        for outbox_file_name in outbox_file_names:
            outbox_file_path = os.path.join(directory.path, outbox_file_name)
            # create folders if they do not exist
            os.makedirs(os.path.dirname(outbox_file_path), exist_ok=True)
            # write test file
            with open(outbox_file_path, "w", encoding="utf-8") as open_file:
                open_file.write("test")
            resources.append(outbox_file_name)

        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_get_preprint_pdf_url.side_effect = mock_preprint_pdf_url

        # mock the SQS client and queues
        fake_queues = {settings_mock.workflow_starter_queue: FakeSQSQueue(directory)}
        fake_sqs_client.return_value = FakeSQSClient(directory, queues=fake_queues)

        expected_result = activity_class.ACTIVITY_SUCCESS
        # invoke
        result = self.activity.do_activity(self.activity_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertTrue(
            (
                "FindFinishPreprintPDFs, outbox_folder finish_preprint/outbox/,"
                " outbox_s3_key_names: ['finish_preprint/outbox/elife-preprint-84364-v2.xml',"
                " 'finish_preprint/outbox/elife-preprint-95901-v1.xml',"
                " 'finish_preprint/outbox/foo.xml']"
            )
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            "FindFinishPreprintPDFs, parsed preprint_versions: [('84364', '2'), ('95901', '1')]"
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "FindFinishPreprintPDFs, got approved_preprint_versions: "
                "[('95901', '1', 'https://example.org/95901v1.pdf')]"
            )
            in self.activity.logger.loginfo
        )
        self.assertTrue(
            (
                "FindFinishPreprintPDFs, starting a FinishPreprintPublication workflow"
                " for article_id 95901, version 1, with pdf_url https://example.org/95901v1.pdf"
            )
            in self.activity.logger.loginfo
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": True, "activity_status": True},
        )

    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_empty_outbox(
        self,
        fake_outbox_storage_context,
    ):
        "test if no XML is found in the outbox folder"
        directory = TempDirectory()

        resources = []
        fake_outbox_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        expected_result = activity_class.ACTIVITY_SUCCESS
        # invoke
        result = self.activity.do_activity(self.activity_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertTrue(
            "FindFinishPreprintPDFs, no approved files found in the outbox"
            in self.activity.logger.loginfo
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": True, "activity_status": None},
        )

    @patch("provider.outbox_provider.outbox_folder")
    def test_do_activity_no_outbox_folder(
        self,
        fake_outbox_folder,
    ):
        "test if the outbox folder is not found"
        fake_outbox_folder.return_value = None
        expected_result = activity_class.ACTIVITY_PERMANENT_FAILURE
        # invoke
        result = self.activity.do_activity(self.activity_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertEqual(
            ("FindFinishPreprintPDFs, outbox_folder None, failing the workflow"),
            self.activity.logger.logerror,
        )
        self.assertDictEqual(
            self.activity.statuses,
            {"outbox_status": None, "activity_status": None},
        )


class TestParsePreprintXmlPath(unittest.TestCase):
    "tests for parse_preprint_xml_path()"

    def test_parse_preprint_xml_path(self):
        "test parsing a match"
        key_name = "finish_preprint/outbox/elife-preprint-95901-v1.xml"
        expected = ("95901", "1")
        # invoke
        result = activity_module.parse_preprint_xml_path(key_name)
        # assert
        self.assertEqual(result, expected)

    def test_not_parsed(self):
        "test a value which does not produce a match"
        key_name = "unsupported.xml"
        expected = (None, None)
        # invoke
        result = activity_module.parse_preprint_xml_path(key_name)
        # assert
        self.assertEqual(result, expected)


class TestSettings(unittest.TestCase):
    "test if required settings not defined"

    def setUp(self):
        self.reviewed_preprint_api_endpoint = (
            settings_mock.reviewed_preprint_api_endpoint
        )
        self.activity_data = {}

    def tearDown(self):
        # reset the settings_mock value
        settings_mock.reviewed_preprint_api_endpoint = (
            self.reviewed_preprint_api_endpoint
        )

    def test_missing_settings(self):
        "test if settings is missing a required value"
        del settings_mock.reviewed_preprint_api_endpoint
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(self.activity_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "FindFinishPreprintPDFs, reviewed_preprint_api_endpoint in"
                " settings is missing, skipping"
            ),
        )

    def test_blank_settings(self):
        "test if required settings value is blank"
        settings_mock.reviewed_preprint_api_endpoint = ""
        activity_object = activity_class(settings_mock, FakeLogger(), None, None, None)
        # do the activity
        result = activity_object.do_activity(self.activity_data)
        # check assertions
        self.assertEqual(result, activity_class.ACTIVITY_SUCCESS)
        self.assertEqual(
            activity_object.logger.loginfo[-1],
            (
                "FindFinishPreprintPDFs, reviewed_preprint_api_endpoint in"
                " settings is blank, skipping"
            ),
        )
