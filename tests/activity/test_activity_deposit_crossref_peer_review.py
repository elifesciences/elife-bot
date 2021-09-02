import os
import unittest
from mock import patch
from ddt import ddt, data
from elifearticle.article import Article, Contributor
from provider import bigquery, crossref, lax_provider
import activity.activity_DepositCrossrefPeerReview as activity_module
from activity.activity_DepositCrossrefPeerReview import (
    activity_DepositCrossrefPeerReview,
)
from tests import bigquery_test_data
from tests.classes_mock import (
    FakeSMTPServer,
    FakeBigQueryClient,
    FakeBigQueryRowIterator,
)
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
import tests.activity.settings_mock as settings_mock
import tests.activity.test_activity_data as activity_test_data
import tests.activity.helpers as helpers


@ddt
class TestDepositCrossrefPeerReview(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefPeerReview(
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

    @patch.object(bigquery, "get_client")
    @patch.object(activity_module, "check_vor_is_published")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.head")
    @patch("requests.post")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    @data(
        {
            "comment": "Article 15747",
            "article_xml_filenames": ["elife-15747-v2.xml", "elife_poa_e03977.xml"],
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
                '<peer_review stage="pre-publication" type="editor-report">',
                "<title>Decision letter: Community-level cohesion without cooperation</title>",
                "<review_date>",
                "<month>05</month>",
                "<month>06</month>",
                "<ai:license_ref>http://creativecommons.org/licenses/by/4.0/</ai:license_ref>",
                '<person_name contributor_role="editor" sequence="first">',
                "<surname>Bergstrom</surname>",
                (
                    '<rel:inter_work_relation identifier-type="doi" relationship-type="isReviewOf">'
                    + "10.7554/eLife.15747</rel:inter_work_relation>"
                ),
                "<doi>10.7554/eLife.15747.010</doi>",
                "<resource>https://elifesciences.org/articles/15747#SA1</resource>",
                '<peer_review stage="pre-publication" type="author-comment">',
                "<title>Author response: Community-level cohesion without cooperation</title>",
                "<doi>10.7554/eLife.15747.011</doi>",
                "<resource>https://elifesciences.org/articles/15747#SA2</resource>",
            ],
        }
    )
    def test_do_activity(
        self,
        test_data,
        fake_storage_context,
        fake_list_resources,
        fake_post_request,
        fake_head_request,
        fake_email_smtp_connect,
        fake_check_vor,
        fake_get_client,
    ):
        fake_check_vor.return_value = True
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_get_client.return_value = True
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        rows = FakeBigQueryRowIterator([bigquery_test_data.ARTICLE_RESULT_15747])
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        # copy XML files into the input directory
        fake_list_resources.return_value = test_data["article_xml_filenames"]
        # mock the POST to endpoint
        fake_post_request.return_value = FakeResponse(test_data.get("post_status_code"))
        fake_head_request.return_value = FakeResponse(302)
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

    @patch.object(bigquery, "get_client")
    @patch.object(activity_module, "check_vor_is_published")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.head")
    @patch("requests.post")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_crossref_exception(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_post_request,
        fake_head_request,
        fake_email_smtp_connect,
        fake_check_vor,
        fake_get_client,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_check_vor.return_value = True
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        rows = FakeBigQueryRowIterator([bigquery_test_data.ARTICLE_RESULT_15747])
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        # copy XML files into the input directory
        fake_list_resources.return_value = [
            "elife-15747-v2.xml",
            "elife_poa_e03977.xml",
        ]

        # raise an exception on a post
        fake_post_request.side_effect = Exception("")
        fake_head_request.return_value = FakeResponse(302)
        result = self.activity.do_activity()
        self.assertTrue(result)

    @patch.object(bigquery, "get_client")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch.object(FakeStorageContext, "list_resources")
    @patch("provider.outbox_provider.storage_context")
    def test_do_activity_no_good_one_bad(
        self,
        fake_storage_context,
        fake_list_resources,
        fake_email_smtp_connect,
        fake_get_client,
    ):
        fake_email_smtp_connect.return_value = FakeSMTPServer(
            self.activity.get_tmp_dir()
        )
        fake_storage_context.return_value = FakeStorageContext("tests/test_data/")
        rows = FakeBigQueryRowIterator([bigquery_test_data.ARTICLE_RESULT_15747])
        client = FakeBigQueryClient(rows)
        fake_get_client.return_value = client
        # copy XML files into the input directory
        fake_list_resources.return_value = ["bad.xml"]

        result = self.activity.do_activity()
        self.assertTrue(result)

    @patch.object(activity_DepositCrossrefPeerReview, "get_manuscript_object")
    def test_get_article_objects(self, fake_manuscript_object):
        """test for parsing an XML file as well as renaming senior_editor to editor"""
        fake_manuscript_object.return_value = bigquery.Manuscript(
            bigquery_test_data.ARTICLE_RESULT_15747
        )
        xml_file_name = "tests/test_data/crossref_peer_review/outbox/elife-32991-v2.xml"
        article_object_map = self.activity.get_article_objects([xml_file_name])
        self.assertEqual(len(article_object_map), 1)
        article_object = article_object_map.get(xml_file_name)
        first_sub_article = article_object.review_articles[0]
        self.assertEqual(len(first_sub_article.contributors), 2)
        self.assertEqual(first_sub_article.contributors[0].contrib_type, "editor")
        self.assertEqual(first_sub_article.contributors[0].surname, "Bronner")
        self.assertEqual(first_sub_article.contributors[1].contrib_type, "editor")
        self.assertEqual(first_sub_article.contributors[1].surname, "Brack")

    @patch.object(activity_DepositCrossrefPeerReview, "get_manuscript_object")
    def test_get_article_objects_dedupe(self, fake_manuscript_object):
        """test for deduping the same editor exists twice"""
        fake_manuscript_object.return_value = bigquery.Manuscript(
            bigquery_test_data.ARTICLE_RESULT_15747
        )
        xml_file_name = "tests/test_data/crossref_peer_review/outbox/elife-32311-v1.xml"
        article_object_map = self.activity.get_article_objects([xml_file_name])
        self.assertEqual(len(article_object_map), 1)
        article_object = article_object_map.get(xml_file_name)
        first_sub_article = article_object.review_articles[0]
        self.assertEqual(len(first_sub_article.contributors), 1)
        self.assertEqual(first_sub_article.contributors[0].contrib_type, "editor")
        self.assertEqual(first_sub_article.contributors[0].surname, "Akhmanova")

    def test_add_editors(self):
        article = Article()
        editor = Contributor("senior_editor", "Aardvark", "Aaron")
        article.editors = [editor]
        sub_article = Article()
        self.activity.add_editors(article, sub_article)
        self.assertEqual(sub_article.contributors[0].surname, "Aardvark")

    def test_set_editor_orcid(self):
        orcid = "0000-0000-0000-000X"
        expected = "https://orcid.org/" + orcid
        sub_article = Article()
        sub_article.contributors = [Contributor("senior_editor", "Baldwin", "Ian")]
        # start with manuscript data then set an ORCID value
        manuscript_object = bigquery.Manuscript(bigquery_test_data.ARTICLE_RESULT_15747)
        manuscript_object.reviewers[0].orcid = orcid
        self.activity.set_editor_orcid(sub_article, manuscript_object)
        self.assertEqual(sub_article.contributors[0].orcid, expected)


class TestPrune(unittest.TestCase):
    def setUp(self):
        article_xml_list = [
            "tests/test_data/crossref_peer_review/outbox/elife-15747-v2.xml",
            "tests/test_data/crossref_peer_review/outbox/elife_poa_e03977.xml",
        ]
        self.article_object_map = crossref.article_xml_list_parse(
            article_xml_list, [], activity_test_data.ExpandArticle_files_dest_folder
        )
        self.logger = FakeLogger()

    def tearDown(self):
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(activity_module, "check_vor_is_published")
    @patch("provider.crossref.doi_exists")
    def test_prune_article_object_map(self, fake_doi_exists, fake_check_vor):
        fake_doi_exists.return_value = True
        fake_check_vor.return_value = True
        good_article_map = activity_module.prune_article_object_map(
            self.article_object_map, settings_mock, self.logger
        )
        self.assertEqual(len(good_article_map), 1)

    @patch.object(activity_module, "check_vor_is_published")
    @patch("provider.crossref.doi_exists")
    def test_prune_article_object_map_doi_not_exists(
        self, fake_doi_exists, fake_check_vor
    ):
        fake_doi_exists.return_value = False
        fake_check_vor.return_value = True
        good_article_map = activity_module.prune_article_object_map(
            self.article_object_map, settings_mock, self.logger
        )
        self.assertEqual(len(good_article_map), 0)

    @patch.object(lax_provider, "article_status_version_map")
    def test_check_vor_is_published_vor(self, fake_version_map):
        article = Article()
        article.id = 666
        fake_version_map.return_value = {"poa": [1], "vor": [2]}
        self.assertTrue(
            activity_module.check_vor_is_published(article, settings_mock, self.logger)
        )

    @patch.object(lax_provider, "article_status_version_map")
    def test_check_vor_is_published_poa(self, fake_version_map):
        article = Article()
        article.id = 666
        fake_version_map.return_value = {"poa": [1]}
        self.assertFalse(
            activity_module.check_vor_is_published(article, settings_mock, self.logger)
        )
