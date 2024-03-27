# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner, lax_provider, preprint
import activity.activity_ScheduleCrossrefPreprint as activity_module
from activity.activity_ScheduleCrossrefPreprint import (
    activity_ScheduleCrossrefPreprint as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import settings_mock


def input_data(article_id=None, version=None, standalone=None):
    activity_data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}
    if article_id is not None:
        activity_data["article_id"] = article_id
    if version is not None:
        activity_data["version"] = version
    if standalone is not None:
        activity_data["standalone"] = standalone
    return activity_data


def session_data(article_id=None, version=None):
    return input_data(article_id, version)


@ddt
class TestScheduleCrossrefPreprint(unittest.TestCase):
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

    @patch("provider.outbox_provider.storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(lax_provider, "article_status_version_map")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap")
    @patch("requests.get")
    @data(
        {
            "comment": "accepted submission zip file example",
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
        fake_version_map,
        fake_download_storage_context,
        fake_outbox_storage_context,
    ):
        directory = TempDirectory()
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_session.return_value = FakeSession(
            session_data(test_data.get("article_id"), test_data.get("version"))
        )
        fake_version_map.return_value = {}
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
        # assert XML is in each outbox folder
        posted_content_outbox_path = os.path.join(
            directory.path, "crossref_posted_content", "outbox"
        )
        self.assertEqual(len(os.listdir(posted_content_outbox_path)), 1)
        peer_review_outbox_path = os.path.join(
            directory.path, "crossref_peer_review", "outbox"
        )
        self.assertEqual(len(os.listdir(peer_review_outbox_path)), 1)
        self.assertEqual(
            os.listdir(peer_review_outbox_path), ["elife-preprint-84364-v2.xml"]
        )

    @patch("provider.outbox_provider.storage_context")
    @patch("provider.download_helper.storage_context")
    @patch.object(lax_provider, "article_status_version_map")
    @patch.object(cleaner, "get_docmap")
    @patch("requests.get")
    @data(
        {
            "comment": "accepted submission zip file example",
            "article_id": "84364",
            "version": 2,
            "standalone": True,
            "expected_result": True,
        },
    )
    def test_do_activity_standalone(
        self,
        test_data,
        fake_get,
        fake_get_docmap,
        fake_version_map,
        fake_download_storage_context,
        fake_outbox_storage_context,
    ):
        "test using standalone data input instead of session"
        directory = TempDirectory()
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_version_map.return_value = {}
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_84364.json")
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        # do the activity
        result = self.activity.do_activity(
            input_data(
                test_data.get("article_id"),
                test_data.get("version"),
                test_data.get("standalone"),
            )
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
    @data(
        {
            "comment": "accepted submission zip file example",
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
            "comment": "accepted submission zip file example",
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
        directory = TempDirectory()
        fake_session.return_value = FakeSession(
            session_data(test_data.get("article_id"), test_data.get("version"))
        )
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
        # assert outbox folders do not exist since no XML was added to them
        posted_content_outbox_path = os.path.join(
            directory.path, "crossref_posted_content", "outbox"
        )
        self.assertEqual(os.path.exists(posted_content_outbox_path), False)
        peer_review_outbox_path = os.path.join(
            directory.path, "crossref_peer_review", "outbox"
        )
        self.assertEqual(os.path.exists(peer_review_outbox_path), False)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "ScheduleCrossrefPreprint, exception raised generating preprint XML"
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
            "comment": "accepted submission zip file example",
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
        directory = TempDirectory()
        exception_message = "An exception"
        fake_generate.side_effect = Exception(exception_message)
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_session.return_value = FakeSession(
            session_data(test_data.get("article_id"), test_data.get("version"))
        )

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
        # assert outbox folders do not exist since no XML was added to them
        posted_content_outbox_path = os.path.join(
            directory.path, "crossref_posted_content", "outbox"
        )
        self.assertEqual(os.path.exists(posted_content_outbox_path), False)
        peer_review_outbox_path = os.path.join(
            directory.path, "crossref_peer_review", "outbox"
        )
        self.assertEqual(os.path.exists(peer_review_outbox_path), False)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "ScheduleCrossrefPreprint, unhandled exception raised"
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
            pass

        # reduce the sleep time to speed up test runs
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = 2

        settings_object = FakeSettings()
        settings_object.downstream_recipients_yaml = (
            settings_mock.downstream_recipients_yaml
        )
        self.activity = activity_object(settings_object, fake_logger, None, None, None)
        self.test_data = {
            "comment": "accepted submission zip file example",
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
        fake_session.return_value = FakeSession(
            session_data(
                self.test_data.get("article_id"), self.test_data.get("version")
            )
        )
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
            "No epp_data_bucket in settings, skipping ScheduleCrossrefPreprint for article_id %s, version %s"
            % (self.test_data.get("article_id"), self.test_data.get("version")),
        )

    @patch.object(activity_module, "get_session")
    def test_blank_bucket_setting(
        self,
        fake_session,
    ):
        "test epp_data_bucket setting is blank"
        self.activity.settings.epp_data_bucket = ""
        fake_session.return_value = FakeSession(
            session_data(
                self.test_data.get("article_id"), self.test_data.get("version")
            )
        )
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
            "epp_data_bucket in settings is blank, skipping ScheduleCrossrefPreprint for article_id %s, version %s"
            % (self.test_data.get("article_id"), self.test_data.get("version")),
        )
