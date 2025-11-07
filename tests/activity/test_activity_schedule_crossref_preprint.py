# coding=utf-8

import os
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_ScheduleCrossrefPreprint as activity_module
from activity.activity_ScheduleCrossrefPreprint import (
    activity_ScheduleCrossrefPreprint as activity_object,
)
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(article_id=None, version=None):
    activity_data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}
    if article_id is not None:
        activity_data["article_id"] = article_id
    if version is not None:
        activity_data["version"] = version
    return activity_data


def session_data(article_id=None, version=None):
    session_dict = test_activity_data.post_preprint_publication_session_example()
    sess_data = input_data(article_id, version)
    for key in ["article_id", "version"]:
        session_dict[key] = sess_data.get(key)
    return session_dict


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
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "non-standalone preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": True,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_session,
        fake_storage_context,
        fake_outbox_storage_context,
    ):
        "non-standalone test which uses the preprint XML from the bucket expanded folder"
        directory = TempDirectory()
        session_dict = session_data(
            test_data.get("article_id"), test_data.get("version")
        )
        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
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
            directory.path, resources, dest_folder=directory.path
        )

        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_session.return_value = FakeSession(session_dict)
        # do the activity
        result = self.activity.do_activity(
            input_data(
                test_data.get("article_id"),
                test_data.get("version"),
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
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "non-standalone preprint article example",
            "article_id": "84364",
            "version": 2,
            "expected_result": activity_object.ACTIVITY_PERMANENT_FAILURE,
        },
    )
    def test_no_xml_in_expanded_folder(
        self,
        test_data,
        fake_session,
        fake_storage_context,
        fake_outbox_storage_context,
    ):
        "test if preprint XML was not found in the bucket expanded folder"
        directory = TempDirectory()
        session_dict = session_data(
            test_data.get("article_id"), test_data.get("version")
        )
        # no bucket resources
        resources = []
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_outbox_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_session.return_value = FakeSession(session_dict)
        # do the activity
        result = self.activity.do_activity(
            input_data(
                test_data.get("article_id"),
                test_data.get("version"),
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
            "comment": "non-standalone preprint article example",
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
        "test session exception raised"
        fake_session.side_effect = Exception("An exception")
        # do the activity
        result = self.activity.do_activity(
            input_data(
                test_data.get("article_id"),
                test_data.get("version"),
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
