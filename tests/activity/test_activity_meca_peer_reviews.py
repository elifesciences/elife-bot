# coding=utf-8

import copy
import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
import activity.activity_MecaPeerReviews as activity_module
from activity.activity_MecaPeerReviews import (
    activity_MecaPeerReviews as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


class TestMecaPeerReviews(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))
        self.session.store_value(
            "docmap_string", read_fixture("sample_docmap_for_95901.json")
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("docmap_string", None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch("requests.get")
    def test_do_activity(
        self,
        fake_get,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()

        fake_session.return_value = self.session

        meca_file_path = "tests/files_source/95901-v1-meca.zip"

        # populate the meca zip file and bucket folders for testing
        populated_data = helpers.populate_meca_test_data(
            meca_file_path, SESSION_DICT, {}, directory.path
        )

        dest_folder = os.path.join(directory.path, "files_dest")

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, populated_data.get("resources"), dest_folder=dest_folder
        )

        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)

        # assert statuses
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("xml_root"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("upload"),
            True,
        )

        xml_file_path = os.path.join(
            dest_folder,
            SESSION_DICT.get("expanded_folder"),
            populated_data.get("xml_file_name"),
        )
        # assertions on XML content
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()

        self.assertTrue("<article" in xml_string)
        self.assertTrue(xml_string.count("<sub-article") == 3)
        # assert peer review DOI value
        self.assertTrue(
            '<article-id pub-id-type="doi">10.7554/eLife.95901.1.sa2</article-id>'
            in xml_string
        )
