import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
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
        self.activity.clean_tmp_dir()
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
        with open(
            "tests/test_data/software_heritage/response_content_example.xml", "rb"
        ) as open_file:
            response_string = open_file.read()
        response.content = response_string
        mock_requests_post.return_value = response

        # do_activity
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )

        # assertions
        self.assertEqual(return_value, self.activity.ACTIVITY_SUCCESS)
        # note: if the assertions below on the loginfo are hard to maintain,
        # they can potentially be removed
        self.assertTrue(
            self.activity.logger.loginfo[34].startswith(
                "PushSWHDeposit, finished post request to "
                "https://deposit.swh.example.org/1/elife/, file path"
            ),
        )
        self.assertEqual(
            self.activity.logger.loginfo[33],
            "Response from SWH API: 201\n%s" % response_string,
        )
        self.assertEqual(
            self.activity.logger.loginfo[32],
            (
                "Post zip file Study_48_Protocols_3_4_Combined_Means.csv.zip "
                "to SWH API: POST https://deposit.swh.example.org/1/elife/"
            ),
        )
        self.assertTrue(
            self.activity.logger.loginfo[6].startswith(
                "PushSWHDeposit, added README.md file to the zip"
            )
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


class TestSplitZipFile(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_split_zip_file(self):
        logger = FakeLogger()
        zip_file_name = "elife-30274-v1-era.zip"
        # create temporary directories for testing
        directory = TempDirectory()
        directory.makedir("input_dir")
        input_dir = os.path.join(directory.path, "input_dir")
        directory.makedir("tmp_dir")
        tmp_dir = os.path.join(directory.path, "tmp_dir")
        # copy the zip file into the input_dir
        zip_file_fixture_path = os.path.join(
            "tests",
            "files_source",
            "software_heritage",
            "run",
            "cf9c7e86-7355-4bb4-b48e-0bc284221251/",
            zip_file_name,
        )
        shutil.copy(zip_file_fixture_path, input_dir)
        zip_file_path = os.path.join(input_dir, zip_file_name)
        # expected values after the function call
        loginfo_expected = [
            "First logger info",
            'split_zip_file, "article.rmd.media/" ends with a slash, skipping it',
            'split_zip_file, "index.html.media/" ends with a slash, skipping it',
            'split_zip_file, "index.html" new zip file name "index.html.zip"',
            (
                'split_zip_file, "Study_48_Protocol_2_Data.csv" '
                'new zip file name "Study_48_Protocol_2_Data.csv.zip"'
            ),
            'split_zip_file, "article.rmd" new zip file name "article.rmd.zip"',
            (
                'split_zip_file, "Study_48_Meta_Analysis.csv" '
                'new zip file name "Study_48_Meta_Analysis.csv.zip"'
            ),
            (
                'split_zip_file, "Study_48_Protocols_3_4_Combined_Means.csv" '
                'new zip file name "Study_48_Protocols_3_4_Combined_Means.csv.zip"'
            ),
            (
                'split_zip_file, "article.references.bib" '
                'new zip file name "article.references.bib.zip"'
            ),
            (
                'split_zip_file, "Study_48_Figure_2_Supplemental_Tables.csv" '
                'new zip file name "Study_48_Figure_2_Supplemental_Tables.csv.zip"'
            ),
            'split_zip_file, "index.html.media/1" new zip file name "index.html.media__1.zip"',
            (
                'split_zip_file, "index.html.media/fig2-figsupp2.jpg" '
                'new zip file name "index.html.media__fig2figsupp2.jpg.zip"'
            ),
            (
                'split_zip_file, "index.html.media/fig1a.png" '
                'new zip file name "index.html.media__fig1a.png.zip"'
            ),
            'split_zip_file, "index.html.media/2" new zip file name "index.html.media__2.zip"',
            (
                'split_zip_file, "index.html.media/fig1.jpg" '
                'new zip file name "index.html.media__fig1.jpg.zip"'
            ),
            (
                'split_zip_file, "index.html.media/fig2.jpg" '
                'new zip file name "index.html.media__fig2.jpg.zip"'
            ),
            (
                'split_zip_file, "index.html.media/fig2-figsupp1.jpg" '
                'new zip file name "index.html.media__fig2figsupp1.jpg.zip"'
            ),
            'split_zip_file, "index.html.media/0" new zip file name "index.html.media__0.zip"',
            (
                'split_zip_file, "index.html.media/fig3.jpg" '
                'new zip file name "index.html.media__fig3.jpg.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig2-figsupp2.jpg" '
                'new zip file name "article.rmd.media__fig2figsupp2.jpg.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig1a.png" '
                'new zip file name "article.rmd.media__fig1a.png.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig1.jpg" '
                'new zip file name "article.rmd.media__fig1.jpg.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig2.jpg" '
                'new zip file name "article.rmd.media__fig2.jpg.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig2-figsupp1.jpg" '
                'new zip file name "article.rmd.media__fig2figsupp1.jpg.zip"'
            ),
            (
                'split_zip_file, "article.rmd.media/fig3.jpg" '
                'new zip file name "article.rmd.media__fig3.jpg.zip"'
            ),
        ]
        return_value_expected = [
            "Study_48_Protocols_3_4_Combined_Means.csv.zip",
            "Study_48_Meta_Analysis.csv.zip",
            "article.rmd.media__fig2.jpg.zip",
            "article.rmd.media__fig1a.png.zip",
            "Study_48_Figure_2_Supplemental_Tables.csv.zip",
            "article.rmd.media__fig3.jpg.zip",
            "index.html.zip",
            "article.references.bib.zip",
            "article.rmd.media__fig1.jpg.zip",
            "index.html.media__2.zip",
            "index.html.media__0.zip",
            "index.html.media__1.zip",
            "article.rmd.media__fig2figsupp1.jpg.zip",
            "Study_48_Protocol_2_Data.csv.zip",
            "index.html.media__fig1.jpg.zip",
            "index.html.media__fig2figsupp1.jpg.zip",
            "article.rmd.zip",
            "article.rmd.media__fig2figsupp2.jpg.zip",
            "index.html.media__fig3.jpg.zip",
            "index.html.media__fig2.jpg.zip",
            "index.html.media__fig2figsupp2.jpg.zip",
            "index.html.media__fig1a.png.zip",
        ]
        # call the function
        return_value = activity_module.split_zip_file(zip_file_path, tmp_dir, logger)
        # test assertions
        self.assertEqual(logger.loginfo, loginfo_expected)
        self.assertEqual(return_value, return_value_expected)


class TestEndpointFromResponse(unittest.TestCase):
    def test_endpoint_from_response(self):
        with open(
            "tests/test_data/software_heritage/response_content_example.xml", "rb"
        ) as open_file:
            response_string = open_file.read()
        endpoint = activity_module.endpoint_from_response(response_string)
        self.assertEqual(
            endpoint, "https://deposit.softwareheritage.org/1/elife/1677/media/"
        )
