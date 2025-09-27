import unittest
from mock import patch
from activity import activity_InvalidatePreprintCdn as activity_module
from activity.activity_InvalidatePreprintCdn import (
    activity_InvalidatePreprintCdn as activity_class,
)
from tests.activity import settings_mock, test_activity_data
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeSession


class TestInvalidatePreprintCdn(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    @patch.object(activity_module, "get_session")
    @patch("provider.fastly_provider.purge_preprint")
    def test_invalidation_success(self, purge_mock, fake_session):
        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )
        purge_mock.return_value = [FakeResponse(200)]
        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)

    @patch.object(activity_module, "get_session")
    @patch("provider.fastly_provider.purge_preprint")
    def test_invalidation_permanent_failure_fastly(self, purge_mock, fake_session):
        fake_session.return_value = FakeSession(
            test_activity_data.ingest_meca_session_example()
        )
        purge_mock.side_effect = Exception("An error occurred calling the Fastly API")
        # invoke
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_module, "get_session")
    def test_session_exception(self, fake_session):
        "test session cannot be animated"
        fake_session.return_value = FakeSession({})
        # invoke
        result = self.activity.do_activity({})
        # assert
        self.assertEqual(result, self.activity.ACTIVITY_PERMANENT_FAILURE)
