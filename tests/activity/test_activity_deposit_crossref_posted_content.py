import os
import time
import unittest
from mock import patch
from testfixtures import TempDirectory
from provider import crossref, lax_provider
import activity.activity_DepositCrossrefPostedContent as activity_module
from activity.activity_DepositCrossrefPostedContent import (
    activity_DepositCrossrefPostedContent,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
from tests.activity import helpers, settings_mock
import tests.activity.test_activity_data as activity_test_data


class TestDepositCrossrefPostedContent(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefPostedContent(
            settings_mock, fake_logger, None, None, None
        )
        self.activity.make_activity_directories()
        self.outbox_folder = "tests/test_data/crossref_posted_content/outbox/"
        self.activity_data = {"sleep_seconds": 0.001}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(lax_provider, "article_status_version_map")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_DepositCrossrefPostedContent, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_post_request,
        fake_version_map,
        fake_email_smtp_connect,
    ):
        test_data = {
            "comment": "Article 84364",
            "article_xml_filenames": ["elife-preprint-84364-v2.xml"],
            "post_status_code": 200,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_outbox_status": True,
            "expected_email_status": True,
            "expected_activity_status": True,
            "expected_file_count": 2,
            "expected_crossref_xml_contains": [
                '<posted_content type="preprint">',
                "<posted_date>",
                "<month>02</month>",
                "<day>13</day>",
                "<year>2023</year>",
                "<doi>10.7554/eLife.84364</doi>",
                "<resource>https://elifesciences.org/reviewed-preprints/84364</resource>",
                "</posted_content>",
            ],
            "expected_crossref_version_xml_contains": [
                '<posted_content type="preprint">',
                "<posted_date>",
                "<month>02</month>",
                "<day>13</day>",
                "<year>2023</year>",
                "<doi>10.7554/eLife.84364.2</doi>",
                "<resource>https://elifesciences.org/reviewed-preprints/84364v2</resource>",
                "</posted_content>",
            ],
        }
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_version_map.return_value = {}
        resources = helpers.populate_storage(
            from_dir=self.outbox_folder,
            to_dir=directory.path,
            filenames=test_data["article_xml_filenames"],
            sub_dir="crossref_posted_content/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        # mock the POST to endpoint
        fake_post_request.return_value = FakeResponse(test_data.get("post_status_code"))
        # do the activity
        result = self.activity.do_activity(self.activity_data)
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
                self.tmp_dir(), sorted(os.listdir(self.tmp_dir()))[0]
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
        if file_count > 0 and test_data.get("expected_crossref_version_xml_contains"):
            # Open the second crossref XML and check some of its contents
            crossref_xml_filename_path = os.path.join(
                self.tmp_dir(), sorted(os.listdir(self.tmp_dir()))[1]
            )
            with open(crossref_xml_filename_path, "rb") as open_file:
                crossref_xml = open_file.read().decode("utf8")
                for expected in test_data.get("expected_crossref_version_xml_contains"):
                    self.assertTrue(
                        expected in crossref_xml,
                        "{expected} not found in crossref_xml {path}".format(
                            expected=expected, path=crossref_xml_filename_path
                        ),
                    )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(lax_provider, "article_status_version_map")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_vor_exists(
        self,
        fake_storage_context,
        fake_post_request,
        fake_version_map,
        fake_email_smtp_connect,
    ):
        "test for if a VOR version already exists"
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_version_map.return_value = {"vor": [1]}
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["elife-preprint-84364-v2.xml"]
        )

        # raise an exception on a post
        fake_post_request.return_value = FakeResponse(200)
        fake_post_request.return_value = True
        fake_post_request.return_value = FakeResponse(200)
        result = self.activity.do_activity(self.activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(lax_provider, "article_status_version_map")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_crossref_exception(
        self,
        fake_storage_context,
        fake_post_request,
        fake_version_map,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_version_map.return_value = {}
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["elife-preprint-84364-v2.xml"]
        )

        # raise an exception on a post
        fake_post_request.side_effect = Exception("")
        fake_post_request.return_value = True
        fake_post_request.return_value = FakeResponse(200)
        result = self.activity.do_activity(self.activity_data)
        self.assertTrue(result)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_no_good_one_bad(
        self,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["bad.xml"]
        )

        result = self.activity.do_activity(self.activity_data)
        self.assertTrue(result)

    def test_get_article_objects(self):
        """test for parsing an XML file"""
        xml_file_name = "%selife-preprint-84364-v2.xml" % self.outbox_folder
        article_object_map = self.activity.get_article_objects([xml_file_name])
        self.assertEqual(len(article_object_map), 1)
        article_object = article_object_map.get(xml_file_name)
        self.assertEqual(article_object.doi, "10.7554/eLife.84364")
        self.assertEqual(
            article_object.get_date("posted_date").date,
            time.strptime("2023-02-13 UTC", "%Y-%m-%d %Z"),
        )


ARTICLE_OBJECT_MAP = crossref.article_xml_list_parse(
    [
        "tests/test_data/crossref_posted_content/outbox/elife-preprint-84364-v2.xml",
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

    @patch.object(lax_provider, "article_status_version_map")
    def test_prune_article_object_map_version_exists(self, fake_version_map):
        fake_version_map.return_value = {"vor": [1]}

        good_article_map = activity_module.prune_article_object_map(
            ARTICLE_OBJECT_MAP, settings_mock, self.logger
        )
        self.assertEqual(len(good_article_map), 0)
