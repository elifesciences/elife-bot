# coding=utf-8

import unittest
import json
from mock import patch
import activity.activity_DepositDOAJ as activity_module
from activity.activity_DepositDOAJ import activity_DepositDOAJ as activity_object
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeSession
from tests import read_fixture
from provider import doaj, lax_provider


class TestDepositDOAJ(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        self.data = {"run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda"}
        self.session = FakeSession(
            {
                "article_id": "65469",
            }
        )
        self.article_json = json.loads(read_fixture("e65469_article_json.txt", "doaj"))

    @patch("requests.post")
    @patch.object(lax_provider, "article_json")
    @patch.object(activity_module, "get_session")
    def test_do_activity(self, mock_session, fake_article_json, fake_post):
        mock_session.return_value = self.session
        fake_article_json.return_value = (200, self.article_json)
        response = FakeResponse(201)
        fake_post.return_value = response
        expected_doaj_json = read_fixture("e65469_doaj_json.py", "doaj")

        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "DepositDOAJ for article_id 65469 statuses: "
                "{'download': True, 'build': True, 'post': True}"
            ),
        )
        doaj_json_loginfo_expected = (
            "DepositDOAJ doaj_json for article_id 65469: %s" % expected_doaj_json
        )
        self.assertEqual(self.activity.logger.loginfo[-2], doaj_json_loginfo_expected)
        self.assertEqual(
            self.activity.logger.loginfo[-3],
            "DepositDOAJ got article_id 65469 from session data",
        )

    @patch("requests.post")
    @patch.object(lax_provider, "article_json")
    def test_do_activity_article_id_from_data(self, fake_article_json, fake_post):
        "test passing the article_id as data rather than from a run session"
        data = {
            "article_id": "65469",
        }
        fake_article_json.return_value = (200, self.article_json)
        response = FakeResponse(201)
        fake_post.return_value = response
        expected_doaj_json = read_fixture("e65469_doaj_json.py", "doaj")

        # do the activity
        result = self.activity.do_activity(data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "DepositDOAJ for article_id 65469 statuses: "
                "{'download': True, 'build': True, 'post': True}"
            ),
        )
        doaj_json_loginfo_expected = (
            "DepositDOAJ doaj_json for article_id 65469: %s" % expected_doaj_json
        )
        self.assertEqual(self.activity.logger.loginfo[-2], doaj_json_loginfo_expected)
        self.assertEqual(
            self.activity.logger.loginfo[-3],
            "DepositDOAJ got article_id 65469 from input data",
        )

    def test_do_activity_settings_no_endpoint(self):
        self.activity.settings = {}
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "No doaj_endpoint in settings, skipping DepositDOAJ.",
        )

    def test_do_activity_settings_blank_endpoint(self):
        self.activity.settings.doaj_endpoint = ""
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "doaj_endpoint in settings is blank, skipping DepositDOAJ.",
        )

    @patch.object(activity_module, "get_session")
    def test_do_activity_session_exception(self, mock_session):
        mock_session.side_effect = Exception("A session exception")
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "Exception in DepositDOAJ getting article_id from session, "
                "run 1ee54f9a-cb28-4c8e-8232-4b317cf4beda: A session exception"
            ),
        )

    @patch.object(lax_provider, "article_json")
    @patch.object(activity_module, "get_session")
    def test_do_activity_lax_exception(self, mock_session, fake_article_json):
        mock_session.return_value = self.session
        fake_article_json.side_effect = Exception("A lax exception")
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_TEMPORARY_FAILURE)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "Exception in DepositDOAJ getting article json using lax_provider, "
                "article_id 65469: A lax exception"
            ),
        )

    @patch.object(lax_provider, "article_json")
    @patch.object(activity_module, "get_session")
    def test_do_activity_article_poa_status(self, mock_session, fake_article_json):
        mock_session.return_value = self.session
        poa_article_json = self.article_json
        poa_article_json["status"] = "poa"
        fake_article_json.return_value = (200, poa_article_json)
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            (
                "DepositDOAJ, article_id 65469 is not VoR status and will not be deposited"
            ),
        )

    @patch.object(doaj, "doaj_json")
    @patch.object(lax_provider, "article_json")
    @patch.object(activity_module, "get_session")
    def test_do_activity_json_build_exception(
        self, mock_session, fake_article_json, fake_doaj_json
    ):
        mock_session.return_value = self.session
        fake_article_json.return_value = (200, self.article_json)
        fake_doaj_json.side_effect = Exception("Exception building json")
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "Exception in DepositDOAJ building DOAJ json, "
                "article_id 65469: Exception building json"
            ),
        )

    @patch("requests.post")
    @patch.object(lax_provider, "article_json")
    @patch.object(activity_module, "get_session")
    def test_do_activity_doaj_exception(
        self, mock_session, fake_article_json, fake_post
    ):
        mock_session.return_value = self.session
        fake_article_json.return_value = (200, self.article_json)
        fake_post.side_effect = Exception("DOAJ endpoint exception")
        # do the activity
        result = self.activity.do_activity(self.data)

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_TEMPORARY_FAILURE)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "Exception in DepositDOAJ posting to DOAJ API endpoint, "
                "article_id 65469: DOAJ endpoint exception"
            ),
        )
