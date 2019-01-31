import os
import unittest
import shutil
import copy
from mock import patch
from tests.classes_mock import FakeSMTPServer
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
from ddt import ddt, data
from provider.templates import Templates
from provider.article import article
import activity.activity_EmailVideoArticlePublished as activity_module
from activity.activity_EmailVideoArticlePublished import (
    activity_EmailVideoArticlePublished as activity_object)


BASE_ACTIVITY_DATA = {
    "run": "",
    "article_id": "00353",
    "version": "1",
    "status": "vor",
    "expanded_folder": "email_video"
    }


def activity_data(data, article_id, status, run_type):
    "customise the input data for test scenarios"
    new_data = copy.copy(data)
    new_data["article_id"] = article_id
    new_data["status"] = status
    new_data["run_type"] = run_type
    return new_data


@ddt
class TestEmailVideoArticlePublished(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        self.activity.clean_tmp_dir()

    def fake_download_video_email_templates(self, to_dir, templates_warmed):
        template_list = self.activity.templates.get_video_email_templates_list()
        for filename in template_list:
            source_doc = "tests/test_data/templates/" + filename
            dest_doc = os.path.join(to_dir, filename)
            shutil.copy(source_doc, dest_doc)
        self.activity.templates.email_templates_warmed = templates_warmed

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch.object(Templates, 'download_video_email_templates_from_s3')
    @patch('provider.lax_provider.article_first_by_status')
    @patch('provider.lax_provider.get_xml_file_name')
    @patch('activity.activity_EmailVideoArticlePublished.storage_context')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "article has video and not a duplicate email",
            "xml_file": "elife-00007-v1.xml",
            "templates_warmed": True,
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00007", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "poa article does not send an email",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00007", "poa", None),
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "silent correction article does not send an email",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00007", "vor", "silent-correction"),
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "article is not the first VoR",
            "xml_file": "elife-00007-v1.xml",
            "templates_warmed": True,
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00007", "vor", None),
            "first_vor": None,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "article does not have a video",
            "xml_file": "elife-00353-v1.xml",
            "templates_warmed": None,
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00353", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "article has video but templates were not downloaded",
            "xml_file": "elife-00007-v1.xml",
            "templates_warmed": False,
            "input_data": activity_data(BASE_ACTIVITY_DATA, "00007", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_PERMANENT_FAILURE
        }
    )
    def test_do_activity(self, test_data, fake_emit, fake_storage_context,
                         fake_get_xml_file_name, fake_first,
                         fake_download_email_templates,
                         fake_email_smtp_connect):
        # mock objects
        fake_emit.return_value = None
        fake_get_xml_file_name.return_value = test_data.get("xml_file")
        fake_first.return_value = test_data.get("first_vor")
        fake_storage_context.return_value = FakeStorageContext()
        fake_download_email_templates.return_value = self.fake_download_video_email_templates(
            self.activity.get_tmp_dir(), test_data.get("templates_warmed"))
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        # do the activity
        success = self.activity.do_activity(test_data.get("input_data"))
        # check assertions
        self.assertEqual(success, test_data.get("activity_success"))

    @patch.object(Templates, 'download_video_email_templates_from_s3')
    def test_template_get_email_headers_00013(self, fake_download_email_templates):

        fake_download_email_templates.return_value = self.fake_download_video_email_templates(
            self.activity.get_tmp_dir(), True)

        email_type = "video_article_publication"

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife00013.xml")

        recipient = {"first_nm": "Features"}

        email_format = "html"

        expected_headers = {
            'format': 'html',
            u'email_type': u'video_article_publication',
            u'sender_email': u'press@elifesciences.org',
            u'subject': u'Features, article 00013 contains a video'}

        body = self.activity.templates.get_email_headers(
            email_type=email_type,
            author=recipient,
            article=article_object,
            format=email_format)

        self.assertEqual(body, expected_headers)

    @patch.object(Templates, 'download_video_email_templates_from_s3')
    def test_template_get_email_body_00353(self, fake_download_email_templates):

        fake_download_email_templates.return_value = self.fake_download_video_email_templates(
            self.activity.get_tmp_dir(), True)

        email_type = "video_article_publication"

        article_object = article()
        article_object.parse_article_file("tests/test_data/elife-00353-v1.xml")

        authors = None
        recipient = {"first_nm": "Features"}

        email_format = "html"

        expected_body = (
            'Header\n<p>Dear Features, article 00353 contains a video. ' +
            'You can <a href="https://doi.org/10.7554/eLife.00353">' +
            'read it</a> online.</p>\nFooter')

        body = self.activity.templates.get_email_body(
            email_type=email_type,
            author=recipient,
            article=article_object,
            authors=authors,
            format=email_format)

        self.assertEqual(body, expected_body)


if __name__ == '__main__':
    unittest.main()
