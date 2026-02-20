import datetime
import os
import re
import time
import unittest
from mock import patch
from testfixtures import TempDirectory
from elifearticle.article import Article
from provider import crossref, utils
import activity.activity_DepositCrossrefPendingPublication as activity_module
from activity.activity_DepositCrossrefPendingPublication import (
    activity_DepositCrossrefPendingPublication,
)
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
from tests.activity import helpers, settings_mock
import tests.activity.test_activity_data as activity_test_data


def mock_doi_does_not_exists(doi, logger, user_agent):
    "return True or False for specific DOI values"
    if doi == "10.7554/eLife.64719":
        return False
    return True


class TestDepositCrossrefPendingPublication(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefPendingPublication(
            settings_mock, fake_logger, None, None, None
        )
        self.activity.make_activity_directories()
        self.outbox_folder = "tests/test_data/crossref_pending_publication/outbox/"

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_DepositCrossrefPendingPublication, "clean_tmp_dir")
    def test_do_activity(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_post_request,
        fake_doi_does_not_exist,
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
            "expected_file_count": 2,
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
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        resources = helpers.populate_storage(
            from_dir=self.outbox_folder,
            to_dir=directory.path,
            filenames=test_data["article_xml_filenames"],
            sub_dir="crossref_pending_publication/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        # mock the POST to endpoint
        fake_post_request.return_value = FakeResponse(test_data.get("post_status_code"))
        fake_doi_does_not_exist.return_value = True
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

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_DepositCrossrefPendingPublication, "clean_tmp_dir")
    def test_do_activity_no_accepted_date(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_email_smtp_connect,
        fake_get_current_datetime,
    ):
        "test if there is no accepted date in the XML"
        accepted_date = "2026-02-01"
        test_data = {
            "comment": "Article 64719",
            "article_xml_filename": "08-11-2020-FA-eLife-64719.xml",
            "post_status_code": 200,
            "expected_result": True,
            "expected_file_count": 2,
            "expected_crossref_xml_contains": [
                "<pending_publication>",
                "<acceptance_date>",
                "<month>02</month>",
                "<day>01</day>",
                "<year>2026</year>",
                "<doi>10.7554/eLife.64719</doi>",
                "</pending_publication>",
            ],
        }
        directory = TempDirectory()
        # prepare XML fixture data to not have an accepted date
        temp_dir = os.path.join(directory.path, "temp")
        os.mkdir(temp_dir)
        xml_file_name = "elife-64719.xml"
        xml_file_path = os.path.join(temp_dir, xml_file_name)
        with open(
            os.path.join(self.outbox_folder, test_data.get("article_xml_filename")),
            "r",
            encoding="utf-8",
        ) as open_file:
            xml_string = open_file.read()
        # remove the accepted date XML
        xml_string = re.sub(
            (
                r'<date date-type="accepted">\n'
                r".*<day>.*?</day>\n"
                r".*<month>.*?</month>\n"
                r".*<year>.*?</year>\n"
                r".*</date>"
            ),
            "",
            xml_string,
        )
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)

        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        resources = helpers.populate_storage(
            from_dir=temp_dir,
            to_dir=directory.path,
            filenames=[xml_file_name],
            sub_dir="crossref_pending_publication/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        # mock the POST to endpoint
        fake_post_request.return_value = FakeResponse(test_data.get("post_status_code"))
        fake_doi_does_not_exist.return_value = True
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            accepted_date, "%Y-%m-%d"
        )

        # do the activity
        result = self.activity.do_activity()
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))

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

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_DepositCrossrefPendingPublication, "clean_tmp_dir")
    def test_do_activity_one_doi_exists(
        self,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_email_smtp_connect,
    ):
        "test for when the concept DOI exists and the version DOI does not exist"
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        resources = helpers.populate_storage(
            from_dir=self.outbox_folder,
            to_dir=directory.path,
            filenames=["08-11-2020-FA-eLife-64719.xml"],
            sub_dir="crossref_pending_publication/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_doi_does_not_exist.side_effect = mock_doi_does_not_exists
        fake_post_request.return_value = FakeResponse(200)

        result = self.activity.do_activity()
        self.assertEqual(result, True)
        self.assertTrue(
            "Moving files from outbox folder to the not_published folder"
            in self.activity.logger.loginfo
        )
        file_count = len(os.listdir(self.tmp_dir()))
        # assert just one deposit file was generated
        self.assertEqual(file_count, 1)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_doi_exists(
        self,
        fake_storage_context,
        fake_doi_does_not_exist,
        fake_email_smtp_connect,
    ):
        "test for when all the DOI already exists"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        resources = helpers.populate_storage(
            from_dir=self.outbox_folder,
            to_dir=directory.path,
            filenames=["08-11-2020-FA-eLife-64719.xml"],
            sub_dir="crossref_pending_publication/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_doi_does_not_exist.return_value = False

        result = self.activity.do_activity()
        self.assertEqual(result, True)
        self.assertTrue(
            "Moving files from outbox folder to the not_published folder"
            in self.activity.logger.loginfo
        )

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.generate.build_crossref_xml")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_crossref_generation_exception(
        self,
        fake_storage_context,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_build,
        fake_email_smtp_connect,
    ):
        "fake a Crossref generation failure to produce a bad_xml_files list"
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["08-11-2020-FA-eLife-64719.xml"]
        )
        # raise an exception on a post
        fake_doi_does_not_exist.return_value = True
        fake_build.side_effect = Exception("An exception")
        fake_post_request.return_value = FakeResponse(200)
        result = self.activity.do_activity()
        self.assertEqual(result, True)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.crossref.doi_does_not_exist")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_crossref_deposit_exception(
        self,
        fake_storage_context,
        fake_post_request,
        fake_doi_does_not_exist,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["08-11-2020-FA-eLife-64719.xml"]
        )

        # raise an exception on a post
        fake_post_request.side_effect = Exception("")
        fake_doi_does_not_exist.return_value = True
        result = self.activity.do_activity()
        self.assertEqual(result, True)

    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_no_good_one_bad(
        self,
        fake_storage_context,
        fake_email_smtp_connect,
    ):
        directory = TempDirectory()
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        fake_storage_context.return_value = FakeStorageContext(
            self.outbox_folder, ["bad.xml"]
        )

        result = self.activity.do_activity()
        self.assertEqual(result, True)

    def test_get_article_objects(self):
        """test for parsing an XML file"""
        xml_file_name = "%s08-11-2020-FA-eLife-64719.xml" % self.outbox_folder
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


class TestArticleTitleRewrite(unittest.TestCase):
    def test_article_title_rewrite(self):
        filename = "filename.xml"
        article = Article()
        article_object_map = {filename: article}
        article_object_map = activity_module.article_title_rewrite(article_object_map)
        self.assertEqual(
            article_object_map.get(filename).title,
            activity_module.PLACEHOLDER_ARTICLE_TITLE,
        )
