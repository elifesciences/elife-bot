import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import github_provider, meca, sts
from activity import activity_ExpandMeca as activity_module
from activity.activity_ExpandMeca import (
    activity_ExpandMeca as activity_class,
)
from tests import list_files
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeGithubIssue,
    FakeLogger,
    FakeStorageContext,
    FakeSession,
    FakeStsClient,
)


class TestExpandMeca(unittest.TestCase):
    "tests for do_activity()"

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity(
        self,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
    ):
        directory = TempDirectory()
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        mock_session = FakeSession(test_activity_data.meca_details_session_example())
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_files = [
            "content/24301711.pdf",
            "content/24301711.xml",
            "content/24301711v1_fig1.tif",
            "content/24301711v1_tbl1.tif",
            "content/24301711v1_tbl1a.tif",
            "content/24301711v1_tbl2.tif",
            "content/24301711v1_tbl3.tif",
            "content/24301711v1_tbl4.tif",
            "directives.xml",
            "manifest.xml",
            "mimetype",
            "transfer.xml",
        ]
        expected_session_dict = test_activity_data.ingest_meca_session_example()
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # Check destination folder files
        bucket_folder_path = os.path.join(
            directory.path,
            mock_session.session_dict.get("expanded_folder"),
        )
        # collect bucket folder file names plus one folder deep file names
        files = list_files(bucket_folder_path)
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(sorted(compare_files), sorted(expected_files))
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "ExpandMeca expanding file %s/95901-v1-meca.zip"
            % self.activity.directories.get("INPUT_DIR")
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)

    @patch.object(sts, "get_client")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_external_bucket_source(
        self,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
        fake_sts_client,
    ):
        "test downloading from an external bucket requiring an STS token"
        directory = TempDirectory()
        from_computer_file_url = "s3://prod-elife-epp-meca/95901-v1-meca.zip"
        to_computer_file_url = "s3://server-src-daily/95901-v1-meca.zip"
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        session_dict = test_activity_data.meca_details_session_example(
            computer_file_url=to_computer_file_url
        )
        session_dict["docmap_string"] = session_dict["docmap_string"].replace(
            from_computer_file_url,
            to_computer_file_url,
        )
        mock_session = FakeSession(session_dict)
        fake_session.return_value = mock_session
        fake_sts_client.return_value = FakeStsClient()
        expected_result = self.activity.ACTIVITY_SUCCESS
        expected_files = [
            "content/24301711.pdf",
            "content/24301711.xml",
            "content/24301711v1_fig1.tif",
            "content/24301711v1_tbl1.tif",
            "content/24301711v1_tbl1a.tif",
            "content/24301711v1_tbl2.tif",
            "content/24301711v1_tbl3.tif",
            "content/24301711v1_tbl4.tif",
            "directives.xml",
            "manifest.xml",
            "mimetype",
            "transfer.xml",
        ]
        expected_session_dict = test_activity_data.ingest_meca_session_example(
            computer_file_url=to_computer_file_url
        )
        expected_session_dict["docmap_string"] = expected_session_dict[
            "docmap_string"
        ].replace(
            from_computer_file_url,
            to_computer_file_url,
        )
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # Check destination folder files
        bucket_folder_path = os.path.join(
            directory.path,
            mock_session.session_dict.get("expanded_folder"),
        )
        # collect bucket folder file names plus one folder deep file names
        files = list_files(bucket_folder_path)
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(sorted(compare_files), sorted(expected_files))
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "ExpandMeca expanding file %s/95901-v1-meca.zip"
            % self.activity.directories.get("INPUT_DIR")
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "download_file_from_s3")
    def test_download_meca_activity_exception(
        self, fake_download, fake_storage_context, fake_session
    ):
        "test an exception during the download procedure"
        directory = TempDirectory()

        mock_session = FakeSession(test_activity_data.meca_details_session_example())
        fake_session.return_value = mock_session
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        exception_string = "Message"
        fake_download.side_effect = Exception(exception_string)
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "ExpandMeca, exception when downloading MECA file 95901-v1-meca.zip: %s"
            % exception_string,
        )

    @patch.object(github_provider, "find_github_issue")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "meca_assume_role")
    def test_assume_role_exception(
        self,
        fake_meca_assume_role,
        fake_storage_context,
        fake_session,
        fake_find_github_issue,
    ):
        "test an exception when assuming a role with STS"
        directory = TempDirectory()
        fake_find_github_issue.return_value = FakeGithubIssue()
        mock_session = FakeSession(
            test_activity_data.meca_details_session_example(
                computer_file_url="s3://server-src-daily/95901-v1-meca.zip"
            )
        )
        fake_session.return_value = mock_session
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        exception_string = "An exception"
        fake_meca_assume_role.side_effect = Exception(exception_string)
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "ExpandMeca, exception when assuming role to access bucket"
                " server-src-daily for 95901-v1-meca.zip: %s" % exception_string
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(FakeStorageContext, "set_resource_from_filename")
    def test_set_resource_exception(
        self,
        fake_set_resource,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
    ):
        "test an exception during adding objects to the S3 bucket expanded folder"
        directory = TempDirectory()
        exception_string = "An exception"
        fake_set_resource.side_effect = Exception(exception_string)
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        mock_session = FakeSession(test_activity_data.meca_details_session_example())
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "ExpandMeca, exception when expanding MECA file 95901-v1-meca.zip: %s"
            % exception_string,
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(meca, "get_meca_article_xml_path")
    def test_no_article_xml_path(
        self,
        fake_get_meca_article_xml_path,
        fake_download_storage_context,
        fake_storage_context,
        fake_session,
    ):
        "test if no article XML is found in manifest.xml"
        directory = TempDirectory()
        mock_session = FakeSession(test_activity_data.meca_details_session_example())
        fake_session.return_value = mock_session
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_get_meca_article_xml_path.return_value = None
        expected_result = self.activity.ACTIVITY_PERMANENT_FAILURE
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, expected_result)


class TestMecaAssumeRole(unittest.TestCase):
    "tests for meca_assume_role()"

    @patch.object(sts, "get_client")
    def test_meca_assume_role(self, fake_sts_client):
        "test assume_role using an STS client"
        logger = FakeLogger()
        fake_sts_client.return_value = FakeStsClient()
        # invoke
        result = activity_module.meca_assume_role(settings_mock, logger)
        # assert
        self.assertTrue(getattr(result, "aws_access_key_id"))

    @patch.object(sts, "assume_role")
    @patch.object(sts, "get_client")
    def test_no_response(self, fake_sts_client, fake_assume_role):
        "test no response returned from the STS client"
        logger = FakeLogger()
        fake_sts_client.return_value = FakeStsClient()
        fake_assume_role.return_value = None
        # invoke
        result = activity_module.meca_assume_role(settings_mock, logger)
        # assert
        self.assertEqual(result, None)

    @patch.object(sts, "assume_role")
    @patch.object(sts, "get_client")
    def test_no_credentials(self, fake_sts_client, fake_assume_role):
        "test no credentials in the response returned from the STS client"
        logger = FakeLogger()
        fake_sts_client.return_value = FakeStsClient()
        fake_assume_role.return_value = {"Credentials": {}}
        # invoke
        result = activity_module.meca_assume_role(settings_mock, logger)
        # assert
        self.assertEqual(result, None)

    def test_no_arn(self):
        "test if there is no arn in the settings"
        logger = FakeLogger()

        class TestSettings:
            pass

        test_settings = TestSettings()
        # invoke
        result = activity_module.meca_assume_role(test_settings, logger)
        # assert
        self.assertEqual(result, None)

    def test_no_session_name(self):
        "test if there is no session name in the settings"
        logger = FakeLogger()

        class TestSettings:
            meca_sts_role_arn = "arn"

        test_settings = TestSettings()
        # invoke
        result = activity_module.meca_assume_role(test_settings, logger)
        # assert
        self.assertEqual(result, None)
