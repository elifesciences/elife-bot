import unittest
from mock import patch
import activity.activity_PushSWHDeposit as activity_module
from activity.activity_PushSWHDeposit import (
    activity_PushSWHDeposit as activity_object,
)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeStorageContext,
    FakeSession,
)
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


class TestPushSWHDeposit(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("requests.post")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(self, mock_storage_context, mock_session, mock_requests_post):
        mock_storage_context.return_value = FakeStorageContext("tests/files_source")
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        response = FakeResponse(201)
        response.content = "SWH endpoint response"
        mock_requests_post.return_value = response

        # do_activity
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )

        # assertions
        self.assertEqual(return_value, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-2],
            "Response from SWH API: 201\nSWH endpoint response",
        )
        self.assertEqual(
            self.activity.logger.loginfo[-3],
            (
                "Post zip file elife-30274-v1-era.zip and atom file elife-30274-v1-era.xml "
                "to SWH API: POST https://deposit.swh.example.org/1/elife/"
            ),
        )

    @patch("requests.post")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_401(
        self, mock_storage_context, mock_session, mock_requests_post
    ):
        mock_storage_context.return_value = FakeStorageContext("tests/files_source")
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        response = FakeResponse(401)
        mock_requests_post.return_value = response

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )

        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_module, "get_session")
    def test_do_activity_no_endpoint_in_settings(self, mock_session):
        # set endpoint setting to blank string
        self.activity.settings.software_heritage_deposit_endpoint = ""
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )

        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "PushSWHDeposit, software_heritage_deposit_endpoint setting is empty or missing",
        )
