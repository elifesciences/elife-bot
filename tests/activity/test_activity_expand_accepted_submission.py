import os
import unittest
from mock import mock, patch
from ddt import ddt, data
from activity import activity_ExpandAcceptedSubmission as activity_module
from activity.activity_ExpandAcceptedSubmission import (
    activity_ExpandAcceptedSubmission as activity_class,
)
import tests.activity.settings_mock as settings_mock
import tests.activity.classes_mock as classes_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext, FakeSession
import tests.activity.test_activity_data as testdata
import tests.test_data as test_case_data
import tests.activity.helpers as helpers


@ddt
class TestExpandAcceptedSubmission(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_class(settings_mock, self.logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "storage_context")
    def test_do_activity(
        self, fake_download_storage_context, fake_storage_context, fake_session
    ):
        fake_download_storage_context.return_value = FakeStorageContext()
        fake_storage_context.return_value = FakeStorageContext()
        mock_session = FakeSession({})
        fake_session.return_value = mock_session
        expected_files = [
            "30-01-2019-RA-eLife-45644.pdf",
            "30-01-2019-RA-eLife-45644.xml",
            "Answers for the eLife digest.docx",
            "Appendix 1.docx",
            "Appendix 1figure 1.png",
            "Appendix 1figure 10.pdf",
            "Appendix 1figure 11.pdf",
            "Appendix 1figure 12.png",
            "Appendix 1figure 13.png",
            "Appendix 1figure 14.png",
            "Appendix 1figure 15.png",
            "Appendix 1figure 2.png",
            "Appendix 1figure 3.png",
            "Appendix 1figure 4.png",
            "Appendix 1figure 5.png",
            "Appendix 1figure 6.png",
            "Appendix 1figure 7.png",
            "Appendix 1figure 8.png",
            "Appendix 1figure 9.png",
            "Figure 1.tif",
            "Figure 2.tif",
            "Figure 3.png",
            "Figure 4.svg",
            "Figure 4source data 1.zip",
            "Figure 5.png",
            "Figure 5source code 1.c",
            "Figure 6.png",
            "Figure 6figure supplement 10_HorC.png",
            "Figure 6figure supplement 1_U crassus.png",
            "Figure 6figure supplement 2_U pictorum.png",
            "Figure 6figure supplement 3_M margaritifera.png",
            "Figure 6figure supplement 4_P auricularius.png",
            "Figure 6figure supplement 5_PesB.png",
            "Figure 6figure supplement 6_HavA.png",
            "Figure 6figure supplement 7_HavB.png",
            "Figure 6figure supplement 8_HavC.png",
            "Figure 6figure supplement 9_HorB.png",
            "Figure 6source data 1.pdf",
            "Manuscript.docx",
            "Potential striking image.tif",
            "Table 2source data 1.xlsx",
            "transparent_reporting_Sakalauskaite.docx",
        ]
        expected_session_dict = {
            "run": "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
            "input_filename": "30-01-2019-RA-eLife-45644.zip",
            "input_bucket_name": "elife-accepted-submission-cleaning",
            "input_bucket_folder": "",
            "expanded_folder": (
                "expanded_submissions/45644/1ee54f9a-cb28-4c8e-8232-4b317cf4beda/expanded_files"
            ),
            "article_id": "45644",
        }
        # do the activity
        success = self.activity.do_activity(
            test_case_data.ingest_accepted_submission_data
        )
        # assertions
        # assert activity return value
        self.assertEqual(True, success)
        # Check destination folder files
        files = sorted(os.listdir(testdata.ExpandArticle_files_dest_folder))
        compare_files = [file_name for file_name in files if file_name != ".gitkeep"]
        self.assertEqual(sorted(compare_files), sorted(expected_files))
        # check session data
        self.assertDictEqual(mock_session.session_dict, expected_session_dict)
        # check logger values
        loginfo_expected = (
            "ExpandAcceptedSubmission expanding file %s"
            % test_case_data.ingest_accepted_submission_data.get("file_name")
        )
        self.assertTrue(loginfo_expected in self.logger.loginfo)

    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module.download_helper, "download_file_from_s3")
    def test_do_activity_exception(
        self, fake_download, fake_storage_context, fake_session
    ):
        "test an exception during the download procedure"
        fake_download.side_effect = Exception("Message")
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession({})

        # todo!! add exception as side_effect
        success = self.activity.do_activity(
            test_case_data.ingest_accepted_submission_data
        )
        self.assertEqual(self.activity.ACTIVITY_PERMANENT_FAILURE, success)
