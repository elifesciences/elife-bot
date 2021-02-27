import os
import shutil
import unittest
from mock import patch
import activity.activity_GenerateSWHMetadata as activity_module
from activity.activity_GenerateSWHMetadata import (
    activity_GenerateSWHMetadata as activity_object,
)
from provider.article import article
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import (
    FakeLogger,
    FakeStorageContext,
    FakeSession,
)
import tests.activity.test_activity_data as testdata
import tests.activity.helpers as helpers


def fake_download_xml(filename, to_dir):
    source_doc = os.path.join("tests", "files_source", "software_heritage", filename)
    dest_doc = os.path.join(to_dir, filename)
    try:
        shutil.copy(source_doc, dest_doc)
        return filename
    except IOError:
        pass
    # default return assume a failure
    return False


class TestGenerateSWHMetadata(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        helpers.delete_files_in_folder("tests/tmp", filter_out=[".keepme"])
        helpers.delete_files_in_folder(
            testdata.ExpandArticle_files_dest_folder, filter_out=[".gitkeep"]
        )

    @patch.object(article, "download_article_xml_from_s3")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self, mock_storage_context, mock_session, fake_download_article_xml
    ):
        article_xml_file = "elife-30274-v2.xml"
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_SUCCESS)

    @patch.object(article, "download_article_xml_from_s3")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_article_xml_exception(
        self, mock_storage_context, mock_session, fake_download_article_xml
    ):
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_article_xml.side_effect = Exception(
            "Exception in downloading article XML"
        )

        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("elifearticle.parse.build_article_from_xml")
    @patch.object(article, "download_article_xml_from_s3")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_article_parse_exception(
        self, mock_storage_context, mock_session, fake_download_article_xml, fake_parse
    ):
        article_xml_file = "elife-30274-v2.xml"
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )
        fake_parse.side_effect = Exception("Exception parsing article XML")
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch("provider.software_heritage.metadata")
    @patch.object(article, "download_article_xml_from_s3")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_metadata_exception(
        self,
        mock_storage_context,
        mock_session,
        fake_download_article_xml,
        fake_metadata,
    ):
        article_xml_file = "elife-30274-v2.xml"
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )
        fake_metadata.side_effect = Exception("Exception generating metadata")
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(FakeStorageContext, "set_resource_from_string")
    @patch.object(article, "download_article_xml_from_s3")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "storage_context")
    def test_do_activity_bucket_exception(
        self,
        mock_storage_context,
        mock_session,
        fake_download_article_xml,
        fake_set_resource,
    ):
        article_xml_file = "elife-30274-v2.xml"
        mock_storage_context.return_value = FakeStorageContext()
        mock_session.return_value = FakeSession(
            testdata.SoftwareHeritageDeposit_session_example
        )
        fake_download_article_xml.return_value = fake_download_xml(
            article_xml_file, self.activity.get_tmp_dir()
        )
        fake_set_resource.side_effect = Exception("Exception uploading metadata")
        return_value = self.activity.do_activity(
            testdata.SoftwareHeritageDeposit_data_example
        )
        self.assertEqual(return_value, self.activity.ACTIVITY_PERMANENT_FAILURE)
