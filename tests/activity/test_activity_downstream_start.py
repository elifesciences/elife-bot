import unittest
from collections import OrderedDict
from mock import patch
from activity.activity_DownstreamStart import activity_DownstreamStart
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession


def data():
    data = OrderedDict()
    data["run"] = "cf9c7e86-7355-4bb4-b48e-0bc284221251"
    data["article_id"] = "30274"
    data["version"] = "1"
    data["workflow"] = "software_heritage"
    data["recipient"] = "software_heritage"
    data["input_file"] = "https://hub.stenci.la/api/projects/518/snapshots/15/archive"
    return data


class TestDownstreamStart(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DownstreamStart(
            settings_mock, fake_logger, None, None, None
        )

    @patch("activity.activity_DownstreamStart.get_session")
    def test_do_activity(self, fake_session):
        fake_session.return_value = FakeSession({})

        result = self.activity.do_activity(data())
        self.assertEqual(self.activity.ACTIVITY_SUCCESS, result)

        print(self.activity.logger.loginfo)
        self.assertEqual(
            self.activity.logger.loginfo[-5:],
            [
                "Stored article_id in session, activity DownstreamStart",
                "Stored input_file in session, activity DownstreamStart",
                "Stored recipient in session, activity DownstreamStart",
                "Stored version in session, activity DownstreamStart",
                "Stored workflow in session, activity DownstreamStart",
            ],
        )

    @patch("activity.activity_DownstreamStart.get_session")
    def test_do_activity_run_exception(self, fake_session):
        fake_session.return_value = FakeSession({})

        result = self.activity.do_activity({})
        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, result)
        self.assertEqual(
            self.activity.logger.logexception,
            "Exception in DownstreamStart do_activity, misisng run value. Error: 'run'",
        )

    @patch("activity.activity_DownstreamStart.get_session")
    def test_do_activity_session_exception(self, fake_session):
        fake_session.side_effect = Exception("Exception in get_session")

        result = self.activity.do_activity(data())
        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, result)
        self.assertEqual(
            self.activity.logger.logexception,
            "Exception in DownstreamStart do_activity. Error: Exception in get_session",
        )
