# coding=utf-8

import copy
import shutil
import unittest
from mock import patch
from ddt import ddt, data
from provider import cleaner
import activity.activity_AcceptedSubmissionDocmap as activity_module
from activity.activity_AcceptedSubmissionDocmap import (
    activity_AcceptedSubmissionDocmap as activity_object,
)
from tests import read_fixture
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
)
from tests.activity import settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


@ddt
class TestAcceptedSubmissionDocmap(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(
            copy.copy(test_activity_data.accepted_session_example)
        )
        self.session.store_value("prc_status", True)
        self.session.store_value(
            "preprint_url", "https://doi.org/10.1101/2021.06.02.446694"
        )
        # reduce the sleep time to speed up test runs
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = 2

    def tearDown(self):
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("docmap_string", None)

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_xml_root_status": True,
            "expected_upload_xml_status": True,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_get_docmap,
        fake_session,
    ):
        "test do_activity()"
        fake_session.return_value = self.session
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_85111.json")
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        # assertions
        self.assertEqual(result, test_data.get("expected_result"))
        self.assertEqual(
            self.session.get_value("docmap_string"),
            read_fixture("sample_docmap_for_85111.json").decode("utf-8"),
        )
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            test_data.get("expected_docmap_string_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )
        self.assertIsNotNone(self.session.get_value("docmap_datetime_string"))

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
            "expected_docmap_string_status": None,
        },
    )
    def test_docmap_exception(
        self,
        test_data,
        fake_get_docmap,
        fake_session,
    ):
        "test if an exception is raised when getting docmap string"
        fake_session.return_value = self.session
        fake_get_docmap.side_effect = Exception("An exception")
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        # assertions
        self.assertEqual(result, test_data.get("expected_result"))
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            test_data.get("expected_docmap_string_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

    @patch.object(activity_module, "get_session")
    @data(
        {
            "comment": "accepted submission zip file example",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "expected_result": True,
        },
    )
    def test_do_activity_not_prc_status(
        self,
        test_data,
        fake_session,
    ):
        # reset prc_status from the session
        self.session.store_value("prc_status", None)
        fake_session.return_value = self.session
        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, test_data.get("expected_result"))
