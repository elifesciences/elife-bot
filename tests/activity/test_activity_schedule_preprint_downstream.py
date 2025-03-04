# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
import activity.activity_SchedulePreprintDownstream as activity_module
from activity.activity_SchedulePreprintDownstream import (
    activity_SchedulePreprintDownstream as activity_object,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import settings_mock


def input_data(article_id=None, version=None, standalone=None, run_type=None):
    activity_data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}
    if article_id is not None:
        activity_data["article_id"] = article_id
    if version is not None:
        activity_data["version"] = version
    if standalone is not None:
        activity_data["standalone"] = standalone
    if run_type is not None:
        activity_data["run_type"] = run_type
    return activity_data


def session_data(article_id=None, version=None):
    sess_data = input_data(article_id, version)
    sess_data["preprint_expanded_folder"] = "preprint.%s.%s/%s" % (
        article_id,
        version,
        sess_data.get("run"),
    )
    return sess_data


@ddt
class TestSchedulePreprintDownstream(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_module, "storage_context")
    @patch("provider.preprint.storage_context")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_SUCCESS,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_session,
        fake_preprint_storage_context,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_preprint_storage_context.return_value = FakeStorageContext(
            resources=["elife-preprint-84364-v2.xml"]
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
        # assert XML is in each outbox folder
        publication_email_outbox_path = os.path.join(
            directory.path, "publication_email", "outbox"
        )
        self.assertEqual(len(os.listdir(publication_email_outbox_path)), 1)
        self.assertEqual(
            os.listdir(publication_email_outbox_path), ["elife-preprint-84364-v2.xml"]
        )

    @patch.object(activity_module, "storage_context")
    @patch("provider.preprint.storage_context")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "preprint article example",
            "article_id": "84364",
            "version": 2,
            "run_type": "silent-correction",
            "expected_result": activity_object.ACTIVITY_SUCCESS,
        },
    )
    def test_silent_correction(
        self,
        test_data,
        fake_session,
        fake_preprint_storage_context,
        fake_storage_context,
    ):
        "test run_type silent-correction"
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_preprint_storage_context.return_value = FakeStorageContext(
            resources=["elife-preprint-84364-v2.xml"]
        )
        fake_session.return_value = FakeSession(
            session_data(test_data.get("article_id"), test_data.get("version"))
        )
        # do the activity
        result = self.activity.do_activity(
            input_data(
                test_data.get("article_id"),
                test_data.get("version"),
                run_type=test_data.get("run_type"),
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
        # assert publication_email outbox does not exist
        publication_email_outbox_path = os.path.join(
            directory.path, "publication_email", "outbox"
        )
        self.assertFalse(os.path.exists(publication_email_outbox_path))

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
    @patch("provider.preprint.expanded_folder_bucket_resource")
    @patch("provider.preprint.find_xml_filename_in_expanded_folder")
    def test_do_activity_exception(
        self,
        fake_find,
        fake_expanded,
        fake_session,
    ):
        "test if an exception is raised in finding preprint XML"
        article_id = "84364"
        version = 2
        expected_result = activity_object.ACTIVITY_TEMPORARY_FAILURE
        fake_session.return_value = FakeSession(session_data(article_id, version))
        fake_expanded.return_value = True
        fake_find.side_effect = Exception("Something went wrong!")
        # do the activity
        result = self.activity.do_activity(input_data(article_id, version))
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "SchedulePreprintDownstream, exception when scheduling downstream deposits"
                " for preprint article_id %s, version %s"
            )
            % (article_id, version),
        )
