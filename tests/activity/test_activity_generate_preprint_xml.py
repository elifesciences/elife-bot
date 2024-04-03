# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner, preprint
import activity.activity_GeneratePreprintXml as activity_module
from activity.activity_GeneratePreprintXml import (
    activity_GeneratePreprintXml as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import settings_mock


def input_data(article_id=None, version=None):
    activity_data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}
    if article_id is not None:
        activity_data["article_id"] = article_id
    if version is not None:
        activity_data["version"] = version
    return activity_data


def session_data():
    "activity starts with a blank session"
    return {}


@ddt
class TestGeneratePreprintXml(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        # reduce the sleep time to speed up test runs
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = 2
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap")
    @patch("requests.get")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": True,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_get,
        fake_get_docmap,
        fake_session,
        fake_download_storage_context,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_storage_context.return_value = FakeStorageContext(
            resources=["elife-preprint-84364-v2.xml"], dest_folder=directory.path
        )
        fake_session.return_value = FakeSession(session_data())
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_84364.json")
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        # do the activity
        result = self.activity.do_activity(
            input_data(test_data.get("article_id"), test_data.get("version"))
        )
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=test_data.get("comment"),
                result=result,
                article_id=test_data.get("article_id"),
            ),
        )
        # assert XML is in the bucket folder
        bucket_outbox_path = os.path.join(
            directory.path, "preprint.84364.2/", "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"
        )
        self.assertEqual(len(os.listdir(bucket_outbox_path)), 1)
        self.assertEqual(
            os.listdir(bucket_outbox_path), ["elife-preprint-84364-v2.xml"]
        )
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "GeneratePreprintXml, copying preprint XML "
                "%s/input_dir/elife-preprint-84364-v2.xml to "
                "s3://origin_bucket/preprint.84364.2/"
                "1ee54f9a-cb28-4c8e-8232-4b317cf4beda/elife-preprint-84364-v2.xml"
            )
            % self.activity.get_tmp_dir(),
        )

    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
        },
    )
    def test_do_activity_session_exception(
        self,
        test_data,
        fake_session,
    ):
        "test using standalone data input instead of session"
        fake_session.side_effect = Exception("An exception")
        # do the activity
        result = self.activity.do_activity(
            input_data(test_data.get("article_id"), test_data.get("version"))
        )
        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=test_data.get("comment"),
                result=result,
                article_id=test_data.get("article_id"),
            ),
        )

    @patch.object(activity_module, "get_session")
    @patch.object(preprint, "generate_preprint_xml")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
        },
    )
    def test_preprint_article_exception(
        self,
        test_data,
        fake_generate,
        fake_session,
    ):
        "test PreprintArticleException exception raised generating preprint XML"
        fake_session.return_value = FakeSession(session_data())
        exception_message = "An exception"
        fake_generate.side_effect = preprint.PreprintArticleException(exception_message)

        # do the activity
        result = self.activity.do_activity(
            input_data(test_data.get("article_id"), test_data.get("version"))
        )

        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=test_data.get("comment"),
                result=result,
                article_id=test_data.get("article_id"),
            ),
        )
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintXml, exception raised generating preprint XML"
                " for article_id %s version %s: %s"
            )
            % (
                test_data.get("article_id"),
                test_data.get("version"),
                exception_message,
            ),
        )

    @patch("provider.download_helper.storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(preprint, "generate_preprint_xml")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
        },
    )
    def test_unhandled_exception(
        self,
        test_data,
        fake_generate,
        fake_session,
        fake_download_storage_context,
    ):
        "test Exception is raised when generating preprint XML"
        exception_message = "An exception"
        fake_generate.side_effect = Exception(exception_message)
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_session.return_value = FakeSession(session_data())

        # do the activity
        result = self.activity.do_activity(
            input_data(test_data.get("article_id"), test_data.get("version"))
        )

        # check assertions
        self.assertEqual(
            result,
            test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=test_data.get("comment"),
                result=result,
                article_id=test_data.get("article_id"),
            ),
        )
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "GeneratePreprintXml, unhandled exception raised"
                " when generating preprint XML"
                " for article_id %s version %s: %s"
            )
            % (
                test_data.get("article_id"),
                test_data.get("version"),
                exception_message,
            ),
        )


class TestSettingsValidation(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()

        class FakeSettings:
            publishing_buckets_prefix = ""
            expanded_bucket = ""

        # reduce the sleep time to speed up test runs
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = 2

        settings_object = FakeSettings()
        settings_object.downstream_recipients_yaml = (
            settings_mock.downstream_recipients_yaml
        )
        self.activity = activity_object(settings_object, fake_logger, None, None, None)
        self.test_data = {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
        }

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "get_session")
    def test_missing_setting(
        self,
        fake_session,
    ):
        "test epp_data_bucket is missing from settings"
        fake_session.return_value = FakeSession(session_data())
        # do the activity
        result = self.activity.do_activity(
            input_data(self.test_data.get("article_id"), self.test_data.get("version"))
        )
        # check assertions
        self.assertEqual(
            result,
            self.test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=self.test_data.get("comment"),
                result=result,
                article_id=self.test_data.get("article_id"),
            ),
        )
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "No epp_data_bucket in settings, skipping GeneratePreprintXml"
                " for article_id %s, version %s"
            )
            % (self.test_data.get("article_id"), self.test_data.get("version")),
        )

    @patch.object(activity_module, "get_session")
    def test_blank_bucket_setting(
        self,
        fake_session,
    ):
        "test epp_data_bucket setting is blank"
        self.activity.settings.epp_data_bucket = ""
        fake_session.return_value = FakeSession(session_data())
        # do the activity
        result = self.activity.do_activity(
            input_data(self.test_data.get("article_id"), self.test_data.get("version"))
        )
        # check assertions
        self.assertEqual(
            result,
            self.test_data.get("expected_result"),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=self.test_data.get("comment"),
                result=result,
                article_id=self.test_data.get("article_id"),
            ),
        )
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "epp_data_bucket in settings is blank, skipping GeneratePreprintXml"
                " for article_id %s, version %s"
            )
            % (self.test_data.get("article_id"), self.test_data.get("version")),
        )
