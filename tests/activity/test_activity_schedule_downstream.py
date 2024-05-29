import unittest
from mock import mock, patch
from testfixtures import TempDirectory
import activity.activity_ScheduleDownstream as activity_module
from activity.activity_ScheduleDownstream import (
    activity_ScheduleDownstream as activity_object,
)
from provider import lax_provider, utils
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
import tests.activity.test_activity_data as activity_test_data


class TestScheduleDownstream(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "get_article_profile_type")
    @patch("provider.lax_provider.article_first_by_status")
    @patch.object(lax_provider, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_do_activity(
        self,
        fake_activity_storage_context,
        fake_storage_context,
        fake_first,
        fake_get_article_profile_type,
    ):
        directory = TempDirectory()
        expected_result = True
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_activity_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_first.return_value = True
        fake_get_article_profile_type.return_value = None
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(activity_module, "get_article_profile_type")
    @patch("provider.lax_provider.article_first_by_status")
    @patch.object(lax_provider, "storage_context")
    @patch.object(activity_module, "storage_context")
    def test_retraction_of_preprint(
        self,
        fake_activity_storage_context,
        fake_storage_context,
        fake_first,
        fake_get_article_profile_type,
    ):
        "test if get_article_profile_type returns retraction_of_preprint"
        directory = TempDirectory()
        expected_result = True
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_activity_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        fake_first.return_value = True
        fake_get_article_profile_type.return_value = "retraction_of_preprint"
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # check assertions
        self.assertEqual(result, expected_result)

    @patch.object(lax_provider, "get_xml_file_name")
    @patch.object(lax_provider, "article_first_by_status")
    def test_do_activity_exception(self, fake_first, fake_get_xml_file_name):
        expected_result = False
        fake_get_xml_file_name.side_effect = Exception("Something went wrong!")
        fake_first.return_value = True
        self.activity.emit_monitor_event = mock.MagicMock()
        # do the activity
        result = self.activity.do_activity(
            activity_test_data.data_example_before_publish
        )
        # check assertions
        self.assertEqual(result, expected_result)


class TestNewOutboxXmlName(unittest.TestCase):
    "tests for new_outbox_xml_name()"

    def test_new_outbox_xml_name(self):
        prefix = "pubmed/outbox"
        journal = "elife"
        article_id = "666"
        result = activity_module.new_outbox_xml_name(
            prefix=prefix, journal=journal, article_id=utils.pad_msid(article_id)
        )
        self.assertEqual(
            result, "%s%s%s.xml" % (prefix, journal, utils.pad_msid(article_id))
        )

    def test_exception(self):
        prefix = "pubmed/outbox"
        journal = "elife"
        article_id = None
        result = activity_module.new_outbox_xml_name(
            prefix=prefix, journal=journal, article_id=article_id
        )
        self.assertEqual(result, None)


class TestGetArticleProfileType(unittest.TestCase):
    "tests for get_article_profile_type()"

    def setUp(self):
        self.xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="retraction">'
            "<article-meta>"
            '<related-article related-article-type="retracted-article" ext-link-type="doi" '
            'xlink:href="10.7554/eLife.00666" id="ra1"/>'
            "</article-meta>"
            "</article>"
        )
        self.expanded_folder_bucket = "bucket"
        self.xml_key_name = "elife00666.xml"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(lax_provider, "article_status_version_map")
    @patch.object(FakeStorageContext, "get_resource_as_string")
    @patch.object(activity_module, "storage_context")
    def test_get_article_profile_type(
        self,
        fake_storage_context,
        fake_string,
        fake_version_map,
    ):
        "test where the retraction related article is status preprint"
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, [], dest_folder=directory.path
        )
        fake_version_map.return_value = {}
        fake_string.return_value = self.xml_string
        expected = "retraction_of_preprint"

        result = activity_module.get_article_profile_type(
            settings_mock, self.expanded_folder_bucket, self.xml_key_name
        )
        self.assertEqual(result, expected)

    @patch.object(lax_provider, "article_status_version_map")
    @patch.object(FakeStorageContext, "get_resource_as_string")
    @patch.object(activity_module, "storage_context")
    def test_related_article_vor(
        self,
        fake_storage_context,
        fake_string,
        fake_version_map,
    ):
        "test where the retraction related article is status vor"
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, [], dest_folder=directory.path
        )
        fake_version_map.return_value = {"vor": [1]}
        fake_string.return_value = self.xml_string
        expected = None

        result = activity_module.get_article_profile_type(
            settings_mock, self.expanded_folder_bucket, self.xml_key_name
        )
        self.assertEqual(result, expected)

    @patch.object(FakeStorageContext, "get_resource_as_string")
    @patch.object(activity_module, "storage_context")
    def test_research_article(
        self,
        fake_storage_context,
        fake_string,
    ):
        "test when article-type is not retraction"
        directory = TempDirectory()
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, [], dest_folder=directory.path
        )
        fake_string.return_value = '<article article=type="research-article" />'
        expected = None

        result = activity_module.get_article_profile_type(
            settings_mock, self.expanded_folder_bucket, self.xml_key_name
        )
        self.assertEqual(result, expected)
