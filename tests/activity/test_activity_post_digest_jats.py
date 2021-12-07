# coding=utf-8

import unittest
from mock import patch
from ddt import ddt, data
from digestparser.objects import Digest
import activity.activity_PostDigestJATS as activity_module
from activity.activity_PostDigestJATS import activity_PostDigestJATS as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeStorageContext
from tests.classes_mock import FakeSMTPServer
import provider.digest_provider as digest_provider


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_digest_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestPostDigestJats(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.post")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(activity_module.digest_provider, "storage_context")
    @data(
        {
            "comment": "digest docx file example",
            "filename": "DIGEST+99999.docx",
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u"https://doi.org/10.7554/eLife.99999",
        },
        {
            "comment": "digest zip file example",
            "filename": "DIGEST+99999.zip",
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u"https://doi.org/10.7554/eLife.99999",
        },
        {
            "comment": "digest file does not exist example",
            "filename": "",
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_jats_status": None,
            "expected_post_status": None,
        },
        {
            "comment": "bad digest docx file example",
            "filename": "DIGEST+99998.docx",
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": None,
            "expected_build_status": False,
            "expected_jats_status": None,
            "expected_post_status": None,
            "expected_email_status": None,
        },
        {
            "comment": "digest author name encoding file example",
            "filename": "DIGEST+99997.zip",
            "post_status_code": 200,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": True,
            "expected_email_status": True,
            "expected_digest_doi": u"https://doi.org/10.7554/eLife.99997",
        },
        {
            "comment": "digest bad post response",
            "filename": "DIGEST+99999.docx",
            "post_status_code": 500,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": True,
            "expected_build_status": True,
            "expected_jats_status": True,
            "expected_post_status": False,
            "expected_email_status": None,
            "expected_digest_doi": u"https://doi.org/10.7554/eLife.99999",
        },
        {
            "comment": "digest silent deposit example",
            "filename": "DIGEST+99999+SILENT.zip",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
            "expected_activity_status": None,
            "expected_build_status": None,
            "expected_jats_status": None,
            "expected_post_status": None,
            "expected_email_status": None,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_storage_context,
        fake_download_storage_context,
        requests_method_mock,
        fake_email_smtp_connect,
    ):
        # copy XML files into the input directory using the storage context
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        # POST response
        requests_method_mock.return_value = FakeResponse(
            test_data.get("post_status_code"), None
        )
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        filename_used = input_data(test_data.get("filename")).get("file_name")
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            (
                "failed in {comment}, got {result}, filename {filename}, "
                + "input_file {input_file}, digest {digest}"
            ).format(
                comment=test_data.get("comment"),
                result=result,
                input_file=self.activity.input_file,
                filename=filename_used,
                digest=self.activity.digest,
            ),
        )
        self.assertEqual(
            self.activity.statuses.get("build"),
            test_data.get("expected_build_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("jats"),
            test_data.get("expected_jats_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("post"),
            test_data.get("expected_post_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertEqual(
            self.activity.statuses.get("email"),
            test_data.get("expected_email_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        # check digest values
        if self.activity.digest and test_data.get("expected_digest_doi"):
            self.assertEqual(
                self.activity.digest.doi,
                test_data.get("expected_digest_doi"),
                "failed in {comment}".format(comment=test_data.get("comment")),
            )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(activity_module.digest_provider, "storage_context")
    @patch.object(digest_provider, "digest_jats")
    def test_do_activity_jats_failure(
        self,
        fake_digest_jats,
        fake_storage_context,
        fake_download_storage_context,
        fake_email_smtp_connect,
    ):
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        activity_data = input_data("DIGEST+99999.zip")
        fake_digest_jats.return_value = None
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(activity_module.download_helper, "storage_context")
    @patch.object(activity_module.digest_provider, "storage_context")
    @patch.object(activity_module.requests_provider, "jats_post_payload")
    def test_do_activity_post_failure(
        self,
        fake_post_jats,
        fake_storage_context,
        fake_download_storage_context,
        fake_email_smtp_connect,
    ):
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        activity_data = input_data("DIGEST+99999.zip")
        fake_post_jats.side_effect = Exception("Something went wrong!")
        result = self.activity.do_activity(activity_data)
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)


class TestPostDigestJatsNoEndpoint(unittest.TestCase):
    def test_do_activity_no_endpoint(self):
        """test returning True if the endpoint is not specified in the settings"""
        activity = activity_object(settings_mock, FakeLogger(), None, None, None)
        # now can safely alter the settings
        del activity.settings.typesetter_digest_endpoint
        result = activity.do_activity()
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)

    def test_do_activity_blank_endpoint(self):
        """test returning True if the endpoint is blank"""
        activity = activity_object(settings_mock, FakeLogger(), None, None, None)
        # now can safely alter the settings
        activity.settings.typesetter_digest_endpoint = ""
        result = activity.do_activity()
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)


class TestEmailErrorReport(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module.email_provider, "smtp_connect")
    def test_email_error_report(self, fake_email_smtp_connect):
        """test sending an email error"""
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        digest_content = Digest()
        digest_content.doi = "10.7554/eLife.99999"
        jats_content = {}
        error_messages = ["An error"]
        settings_mock.typesetter_digest_endpoint = ""
        result = self.activity.email_error_report(
            digest_content, jats_content, error_messages
        )
        self.assertEqual(result, True)


if __name__ == "__main__":
    unittest.main()
