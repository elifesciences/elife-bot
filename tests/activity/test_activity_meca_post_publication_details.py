from datetime import datetime
import unittest
from mock import patch
from provider import cleaner, utils
from activity import activity_MecaDetails as parent_activity_module
from activity.activity_MecaPostPublicationDetails import (
    activity_MecaPostPublicationDetails as activity_class,
)
from tests import read_fixture
from tests.activity import helpers, settings_mock, test_activity_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
)


class TestMecaPostPublicationDetails(unittest.TestCase):
    "tests for do_activity()"

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])

    @patch.object(parent_activity_module, "get_session")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    @patch.object(utils, "get_current_datetime")
    def test_do_activity(
        self,
        fake_datetime,
        fake_get_docmap,
        fake_session,
    ):
        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )
        fake_get_docmap.return_value = read_fixture("sample_docmap_for_95901.json")
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        expected_result = self.activity.ACTIVITY_SUCCESS
        computer_file_url = (
            "s3://prod-elife-epp-meca/reviewed-preprints/95901-v1-meca.zip"
        )
        expected_session_dict = test_activity_data.meca_details_session_example(
            computer_file_url=computer_file_url
        )
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        # assert activity return value
        self.assertEqual(result, expected_result)
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "MecaPostPublicationDetails, computer_file_url %s"
            " for version_doi 10.7554/eLife.95901.1" % computer_file_url
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)
