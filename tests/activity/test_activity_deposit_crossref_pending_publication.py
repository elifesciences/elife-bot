import os
import time
import unittest
from mock import patch
from provider import crossref
import activity.activity_DepositCrossrefPendingPublication as activity_module
from activity.activity_DepositCrossrefPendingPublication import (
    activity_DepositCrossrefPendingPublication,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
import tests.activity.settings_mock as settings_mock
import tests.activity.test_activity_data as activity_test_data
import tests.activity.helpers as helpers


class TestDepositCrossrefPendingPublication(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefPendingPublication(
            settings_mock, fake_logger, None, None, None
        )
        self.activity.make_activity_directories()

    def tearDown(self):
        self.activity.clean_tmp_dir()
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_exists")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_doi_exists,
        fake_email_smtp_connect,
    ):
        test_data = {
            "comment": "Article 64719",
            "article_xml_filenames": ["08-11-2020-FA-eLife-64719.xml"],
            "post_status_code": 200,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_outbox_status": True,
            "expected_email_status": True,
            "expected_activity_status": True,
            "expected_file_count": 1,
            "expected_crossref_xml_contains": [
                "<pending_publication>",
                "<acceptance_date>",
                "<month>06</month>",
                "<day>18</day>",
                "<year>2021</year>",
                "<doi>10.7554/eLife.64719</doi>",
                "</pending_publication>",
            ],
        }
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        # copy XML files into the input directory
        fake_list_resources.return_value = test_data["article_xml_filenames"]
        # mock the POST to endpoint
        fake_post_request.return_value = FakeResponse(test_data.get("post_status_code"))
        fake_doi_does_not_exist.return_value = True
        fake_doi_exists.return_value = False
        # do the activity
        result = self.activity.do_activity()
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in [
            "approve",
            "generate",
            "publish",
            "outbox",
            "email",
            "activity",
        ]:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value,
                expected,
                "{expected} {status_name} status not equal to {status_value} in {comment}".format(
                    expected=expected,
                    status_name=status_name,
                    status_value=status_value,
                    comment=test_data.get("comment"),
                ),
            )
        # Count crossref XML file in the tmp directory
        file_count = len(os.listdir(self.tmp_dir()))
        self.assertEqual(file_count, test_data.get("expected_file_count"))
        if file_count > 0 and test_data.get("expected_crossref_xml_contains"):
            # Open the first crossref XML and check some of its contents
            crossref_xml_filename_path = os.path.join(
                self.tmp_dir(), os.listdir(self.tmp_dir())[0]
            )
            with open(crossref_xml_filename_path, "rb") as open_file:
                crossref_xml = open_file.read().decode("utf8")
                for expected in test_data.get("expected_crossref_xml_contains"):
                    self.assertTrue(
                        expected in crossref_xml,
                        "{expected} not found in crossref_xml {path}".format(
                            expected=expected, path=crossref_xml_filename_path
                        ),
                    )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_exists")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_crossref_exception(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_doi_exists,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        # copy XML files into the input directory
        fake_list_resources.return_value = ["08-11-2020-FA-eLife-64719.xml"]

        # raise an exception on a post
        fake_post_request.side_effect = Exception("")
        fake_doi_does_not_exist.return_value = True
        fake_doi_exists.return_value = False
        fake_post_request.return_value = True
        fake_post_request.return_value = FakeResponse(200)
        result = self.activity.do_activity()
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_no_good_one_bad(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        # copy XML files into the input directory
        fake_list_resources.return_value = ["bad.xml"]

        result = self.activity.do_activity()
        self.assertTrue(result)

    def test_get_article_objects(self):
        """test for parsing an XML file"""
        xml_file_name = (
            "tests/test_data/crossref_pending_publication/"
            "outbox/08-11-2020-FA-eLife-64719.xml"
        )
        article_object_map = self.activity.get_article_objects([xml_file_name])
        self.assertEqual(len(article_object_map), 1)
        article_object = article_object_map.get(xml_file_name)
        self.assertEqual(article_object.doi, "10.7554/eLife.64719")
        self.assertEqual(
            article_object.get_date("accepted").date,
            time.strptime("2021-06-18 UTC", "%Y-%m-%d %Z"),
        )


ARTICLE_OBJECT_MAP = crossref.article_xml_list_parse(
    [
        "tests/test_data/crossref_pending_publication/outbox/08-11-2020-FA-eLife-64719.xml",
    ],
    [],
    activity_test_data.ExpandArticle_files_dest_folder,
)


class TestPrune(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def tearDown(self):
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch("provider.crossref.doi_does_not_exist")
    def test_prune_article_object_map_doi_exists(self, fake_doi_exists):
        fake_doi_exists.return_value = False

        good_article_map = activity_module.prune_article_object_map(
            ARTICLE_OBJECT_MAP, self.logger
        )
        self.assertEqual(len(good_article_map), 0)
