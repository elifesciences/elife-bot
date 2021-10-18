import os
import unittest
import shutil
import copy
from collections import OrderedDict
from mock import patch
from tests.classes_mock import FakeSMTPServer
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext
from ddt import ddt, data
from provider.templates import Templates
from provider.article import article
import provider.article_processing as article_processing
import provider.email_provider as email_provider
import activity.activity_EmailVideoArticlePublished as activity_module
from activity.activity_EmailVideoArticlePublished import (
    activity_EmailVideoArticlePublished as activity_object)


BASE_ACTIVITY_DATA = {
    "run": "",
    "article_id": "353",
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

    @patch.object(activity_module.email_provider, 'smtp_connect')
    @patch('provider.lax_provider.article_first_by_status')
    @patch('provider.lax_provider.get_xml_file_name')
    @patch.object(article_processing, 'storage_context')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "article has video and not a duplicate email",
            "xml_file": "elife-00007-v1.xml",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "7", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "poa article does not send an email",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "7", "poa", None),
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "silent correction article does not send an email",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "7", "vor", "silent-correction"),
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "article is not the first VoR",
            "xml_file": "elife-00007-v1.xml",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "7", "vor", None),
            "first_vor": None,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        },
        {
            "comment": "article does not have a video",
            "xml_file": "elife-00353-v1.xml",
            "input_data": activity_data(BASE_ACTIVITY_DATA, "353", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_SUCCESS
        }
    )
    def test_do_activity(self, test_data, fake_emit,
                         fake_processing_storage_context, fake_get_xml_file_name, fake_first,
                         fake_email_smtp_connect):
        # mock objects
        fake_emit.return_value = None
        fake_processing_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = test_data.get("xml_file")
        fake_first.return_value = test_data.get("first_vor")
        fake_email_smtp_connect.return_value = FakeSMTPServer(self.activity.get_tmp_dir())
        # do the activity
        success = self.activity.do_activity(test_data.get("input_data"))
        # check assertions
        self.assertEqual(success, test_data.get("activity_success"))

    @patch.object(Templates, "copy_email_templates")
    @patch('provider.lax_provider.article_first_by_status')
    @patch('provider.lax_provider.get_xml_file_name')
    @patch.object(article_processing, 'storage_context')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "article has video but templates were not downloaded",
            "xml_file": "elife-00007-v1.xml",
            "templates_warmed": False,
            "input_data": activity_data(BASE_ACTIVITY_DATA, "7", "vor", None),
            "first_vor": True,
            "activity_success": activity_object.ACTIVITY_PERMANENT_FAILURE
        }
    )
    def test_do_activity_templatest_error(self, test_data, fake_emit,
                         fake_processing_storage_context, fake_get_xml_file_name, fake_first,
                         fake_copy_email_templates
                         ):
        # mock objects
        fake_emit.return_value = None
        fake_processing_storage_context.return_value = FakeStorageContext()
        fake_get_xml_file_name.return_value = test_data.get("xml_file")
        fake_first.return_value = test_data.get("first_vor")
        self.activity.templates.email_templates_warmed = False
        # do the activity
        success = self.activity.do_activity(test_data.get("input_data"))
        # check assertions
        self.assertEqual(success, test_data.get("activity_success"))

    @patch.object(email_provider, 'smtp_send_messages')
    @data(
        {
            "recipient": {},
            "email_type": "",
            "expected": False
        },
        {
            "recipient": {"e_mail": "elife@example.org"},
            "email_type": "video_article_publication",
            "expected": False
        },
    )
    def test_send_email(self, test_data, fake_smtp_send_messages):
        """test cases for exceptions in send_email"""
        article_object = article()
        article_object.doi_id = 666
        fake_smtp_send_messages.return_value = OrderedDict([("error", 1), ("success", 1)])
        self.activity.download_templates()
        # call the method
        return_value = self.activity.send_email(
            test_data.get("email_type"), test_data.get("recipient"), article_object)
        # check assertions
        self.assertEqual(return_value, test_data.get("expected"))

    @patch('provider.templates.email_headers')
    @data(
        {
            "recipient": {"e_mail": "elife@example.org"},
            "email_type": "",
            "expected": False
        },
    )
    def test_send_email_header_failure(self, test_data, fake_email_headers):
        """test cases for exception loading header template"""
        article_object = article()
        article_object.doi_id = 666
        fake_email_headers.return_value = None
        # call the method
        return_value = self.activity.send_email(
            test_data.get("email_type"), test_data.get("recipient"), article_object)
        # check assertions
        self.assertEqual(return_value, test_data.get("expected"))

    def test_template_get_email_headers_00013(self):

        self.activity.download_templates()

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

    def test_template_get_email_body_00353(self):

        self.activity.download_templates()

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
