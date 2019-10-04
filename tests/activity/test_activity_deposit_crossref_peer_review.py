import os
import unittest
import shutil
from mock import patch
from ddt import ddt, data
from provider import bigquery
import activity.activity_DepositCrossrefPeerReview as activity_module
from activity.activity_DepositCrossrefPeerReview import activity_DepositCrossrefPeerReview
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
import tests.activity.settings_mock as settings_mock
import tests.activity.test_activity_data as activity_test_data
import tests.activity.helpers as helpers


@ddt
class TestDepositCrossrefPeerReview(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefPeerReview(
            settings_mock, fake_logger, None, None, None)
        self.activity.make_activity_directories()

    def tearDown(self):
        self.activity.clean_tmp_dir()
        helpers.delete_files_in_folder(
            activity_test_data.ExpandArticle_files_dest_folder, filter_out=['.gitkeep'])

    def input_dir(self):
        "return the staging dir name for the activity"
        return self.activity.directories.get("INPUT_DIR")

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    def fake_download_files_from_s3_outbox(self, document):
        source_doc = "tests/test_data/crossref_peer_review/" + document
        dest_doc = self.input_dir() + os.sep + document
        shutil.copy(source_doc, dest_doc)

    @patch.object(bigquery, 'get_review_date')
    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('requests.post')
    @patch.object(FakeStorageContext, 'list_resources')
    @patch('provider.crossref.storage_context')
    @data(
        {
            "comment": "Article 15747",
            "article_xml_filenames": ['elife-15747-v2.xml', 'elife_poa_e03977.xml'],
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
                '<title>Decision letter: Community-level cohesion without cooperation</title>',
                '<review_date>',
                '<month>10</month>',
                '<ai:license_ref>http://creativecommons.org/licenses/by/4.0/</ai:license_ref>',
                '<person_name contributor_role="editor" sequence="first">',
                '<surname>Bergstrom</surname>',
                ('<rel:inter_work_relation identifier-type="doi" relationship-type="isReviewOf">' +
                 '10.7554/eLife.15747</rel:inter_work_relation>'),
                '<doi>10.7554/eLife.15747.010</doi>',
                '<resource>https://elifesciences.org/articles/15747#SA1</resource>',

                '<peer_review stage="pre-publication" type="author-comment">',
                '<title>Author response: Community-level cohesion without cooperation</title>',
                '<doi>10.7554/eLife.15747.011</doi>',
                '<resource>https://elifesciences.org/articles/15747#SA2</resource>'
                ]
        }
    )
    def test_do_activity(self, test_data, fake_storage_context, fake_list_resources,
                         fake_request, fake_email_smtp_connect, get_review_date):
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        fake_storage_context.return_value = FakeStorageContext('tests/test_data/')
        get_review_date.return_value = "2019-10-04"
        # copy XML files into the input directory
        fake_list_resources.return_value = test_data["article_xml_filenames"]
        # mock the POST to endpoint
        fake_request.return_value = FakeResponse(test_data.get("post_status_code"))
        # do the activity
        result = self.activity.do_activity()
        # check assertions
        self.assertEqual(result, test_data.get("expected_result"))
        # check statuses assertions
        for status_name in ['approve', 'generate', 'publish', 'outbox', 'email', 'activity']:
            status_value = self.activity.statuses.get(status_name)
            expected = test_data.get("expected_" + status_name + "_status")
            self.assertEqual(
                status_value, expected,
                '{expected} {status_name} status not equal to {status_value} in {comment}'.format(
                    expected=expected, status_name=status_name, status_value=status_value,
                    comment=test_data.get("comment")))
        # Count crossref XML file in the tmp directory
        file_count = len(os.listdir(self.tmp_dir()))
        self.assertEqual(file_count, test_data.get("expected_file_count"))
        if file_count > 0 and test_data.get("expected_crossref_xml_contains"):
            # Open the first crossref XML and check some of its contents
            crossref_xml_filename_path = os.path.join(self.tmp_dir(), os.listdir(self.tmp_dir())[0])
            with open(crossref_xml_filename_path, 'rb') as open_file:
                crossref_xml = open_file.read().decode('utf8')
                for expected in test_data.get("expected_crossref_xml_contains"):
                    self.assertTrue(
                        expected in crossref_xml,
                        '{expected} not found in crossref_xml {path}'.format(
                            expected=expected, path=crossref_xml_filename_path))


if __name__ == '__main__':
    unittest.main()
