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
from tests.activity import helpers, settings_mock, test_activity_data


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
    sess_data = test_activity_data.post_preprint_publication_session_example()
    if article_id:
        sess_data["article_id"] = article_id
    if version:
        sess_data["version"] = version
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
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "published preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_outbox_folders": ["clockss_preprint", "publication_email"],
            "expected_result": activity_object.ACTIVITY_SUCCESS,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()

        session_dict = session_data(
            test_data.get("article_id"),
            test_data.get("version"),
        )

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
        )
        poa_bucket_folder = os.path.join(directory.path, "poa_bucket")
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        os.makedirs(poa_bucket_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=poa_bucket_folder
        )

        fake_session.return_value = FakeSession(session_dict)
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
        # assert list of outbox folders
        self.assertEqual(
            sorted(os.listdir(poa_bucket_folder)),
            sorted(test_data.get("expected_outbox_folders")),
            ("failed in {comment}, got {result}, article_id {article_id}").format(
                comment=test_data.get("comment"),
                result=result,
                article_id=test_data.get("article_id"),
            ),
        )
        # assert XML is in an outbox folder
        for outbox_folder in test_data.get("expected_outbox_folders"):
            publication_email_outbox_path = os.path.join(
                poa_bucket_folder, outbox_folder, "outbox"
            )
            self.assertEqual(len(os.listdir(publication_email_outbox_path)), 1)
            self.assertEqual(
                os.listdir(publication_email_outbox_path),
                ["elife-preprint-84364-v2.xml"],
            )

    @patch.object(activity_module, "storage_context")
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
        fake_storage_context,
    ):
        "test run_type silent-correction"
        directory = TempDirectory()

        session_dict = session_data(
            test_data.get("article_id"),
            test_data.get("version"),
        )

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
        )
        poa_bucket_folder = os.path.join(directory.path, "poa_bucket")
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        os.makedirs(poa_bucket_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=poa_bucket_folder
        )
        fake_session.return_value = FakeSession(session_dict)

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
            input_data(
                test_data.get("article_id"), test_data.get("version"), standalone=True
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
    @patch.object(activity_module, "storage_context")
    @patch("provider.downstream.choose_outboxes")
    def test_do_activity_exception(
        self,
        fake_choose_outboxes,
        fake_storage_context,
        fake_session,
    ):
        "test if an exception is raised when populating outbox folders"
        directory = TempDirectory()
        article_id = "84364"
        version = 2
        expected_result = activity_object.ACTIVITY_TEMPORARY_FAILURE
        fake_session.return_value = FakeSession(session_data(article_id, version))
        resources = []
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        exception_message = "Something went wrong!"
        fake_choose_outboxes.side_effect = Exception(exception_message)
        # do the activity
        result = self.activity.do_activity(input_data(article_id, version))
        # check assertions
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "SchedulePreprintDownstream, exception when scheduling downstream deposits"
                " for preprint article_id %s, version %s: %s"
            )
            % (article_id, version, exception_message),
        )
