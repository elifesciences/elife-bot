import glob
import os
import unittest
from mock import patch
from ddt import ddt, data
from testfixtures import TempDirectory
from elifecrossref import clinical_trials
from provider import crossref
import activity.activity_DepositCrossrefMinimal as activity_module
from activity.activity_DepositCrossrefMinimal import activity_DepositCrossrefMinimal
from tests.classes_mock import FakeSMTPServer
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
from tests.activity import helpers, settings_mock
import tests.test_data as test_case_data


@ddt
class TestDepositCrossrefMinimal(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_DepositCrossrefMinimal(
            settings_mock, fake_logger, None, None, None
        )
        self.activity.make_activity_directories()
        self.activity_data = {"sleep_seconds": 0.001}

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.activity.clean_tmp_dir()

    def tmp_dir(self):
        "return the tmp dir name for the activity"
        return self.activity.directories.get("TMP_DIR")

    @patch.object(clinical_trials, "registry_name_to_doi_map")
    @patch.object(activity_module.email_provider, "smtp_connect")
    @patch("requests.post")
    @patch("provider.outbox_provider.storage_context")
    @patch.object(activity_DepositCrossrefMinimal, "clean_tmp_dir")
    @data(
        {
            "comment": "Article 1234567890",
            "article_xml_filenames": ["elife-1234567890-v99.xml"],
            "post_status_code": 200,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_outbox_status": True,
            "expected_email_status": True,
            "expected_activity_status": True,
            "expected_file_count": 1,
            "expected_crossref_xml_contains": ["<doi>10.7554/eLife.1234567890</doi>"],
            "expected_crossref_xml_does_not_contain": ["<rel:program>"],
            "expected_email_count": 1,
            "expected_email_subject": "DepositCrossrefMinimal Success! files: 1,",
            "expected_email_from": "From: sender@example.org",
            "expected_email_body_contains": [
                r"DepositCrossrefMinimal status:\n\nSuccess!\n\nactivity_status: True",
                r"Outbox files: \ncrossref_minimal/outbox/elife-1234567890-v99.xml",
                r"Published files generated crossref_minimal XML: \nelife-1234567890-v99.xml",
                "/tmp_dir/elife-crossref-minimal-1234567890-",
                "HTTP status: 200",
            ],
        },
        {
            "comment": "Multiple files to deposit",
            "article_xml_filenames": [
                "elife-1234567890-v99.xml",
                "elife-23065-v1.xml",
                "fake-00000-v1.xml",
            ],
            "post_status_code": 200,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": True,
            "expected_outbox_status": True,
            "expected_email_status": True,
            "expected_activity_status": True,
            "expected_file_count": 2,
        },
        {
            "comment": "No files to deposit",
            "article_xml_filenames": [],
            "post_status_code": 200,
            "expected_result": True,
            "expected_approve_status": False,
            "expected_generate_status": True,
            "expected_publish_status": None,
            "expected_outbox_status": None,
            "expected_email_status": None,
            "expected_activity_status": True,
            "expected_file_count": 0,
        },
        {
            "comment": "API endpoint 404",
            "article_xml_filenames": ["elife-1234567890-v99.xml"],
            "post_status_code": 404,
            "expected_result": True,
            "expected_approve_status": True,
            "expected_generate_status": True,
            "expected_publish_status": False,
            "expected_outbox_status": None,
            "expected_email_status": None,
            "expected_activity_status": False,
            "expected_file_count": 1,
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_storage_context,
        fake_request,
        fake_email_smtp_connect,
        fake_clinical_trial_name_map,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None
        fake_email_smtp_connect.return_value = FakeSMTPServer(directory.path)
        # populate the bucket resources and copy them to the temp directory
        resources = helpers.populate_storage(
            from_dir="tests/test_data/crossref_minimal/outbox",
            to_dir=directory.path,
            filenames=test_data["article_xml_filenames"],
            sub_dir="crossref_minimal/outbox",
        )
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        # mock the POST to endpoint
        fake_request.return_value = FakeResponse(test_data.get("post_status_code"))
        # mock GET response data from Crossref clinical trials endpoint
        fake_clinical_trial_name_map.return_value = {
            "ClinicalTrials.gov": "10.18810/clinical-trials-gov",
            "ChiCTR": "10.18810/chictr",
        }
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

        if file_count > 0 and test_data.get("expected_crossref_xml_does_not_contain"):
            # Open the first crossref XML and check some of its contents
            crossref_xml_filename_path = os.path.join(
                self.tmp_dir(), os.listdir(self.tmp_dir())[0]
            )
            with open(crossref_xml_filename_path, "rb") as open_file:
                crossref_xml = open_file.read().decode("utf8")
                for expected in test_data.get("expected_crossref_xml_does_not_contain"):
                    self.assertTrue(
                        expected not in crossref_xml,
                        "{expected} unexpectedly found in crossref_xml {path}".format(
                            expected=expected, path=crossref_xml_filename_path
                        ),
                    )

        # check email files and contents
        email_files_filter = os.path.join(directory.path, "*.eml")
        email_files = glob.glob(email_files_filter)
        if "expected_email_count" in test_data:
            self.assertEqual(len(email_files), test_data.get("expected_email_count"))
            # can look at the first email for the subject and sender
            first_email_content = None
            with open(email_files[0]) as open_file:
                first_email_content = open_file.read()
            if first_email_content:
                if test_data.get("expected_email_subject"):
                    self.assertTrue(
                        test_data.get("expected_email_subject") in first_email_content
                    )
                if test_data.get("expected_email_from"):
                    self.assertTrue(
                        test_data.get("expected_email_from") in first_email_content
                    )
                if test_data.get("expected_email_body_contains"):
                    body = helpers.body_from_multipart_email_string(first_email_content)
                    for expected_to_contain in test_data.get(
                        "expected_email_body_contains"
                    ):
                        self.assertTrue(expected_to_contain in str(body))

    @patch("provider.lax_provider.article_versions")
    def test_get_article_objects(self, mock_article_versions):
        "example where there is not pub date and no version for an article"
        mock_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        crossref_config = crossref.elifecrossref_config(settings_mock)
        xml_file = "tests/test_data/crossref_minimal/outbox/elife_poa_e03977.xml"
        articles = self.activity.get_article_objects([xml_file], crossref_config)
        article = articles[xml_file]
        self.assertIsNotNone(
            article.get_date("pub"), "date of type pub not found in article get_date()"
        )
        self.assertIsNotNone(article.version, "version is None in article")
