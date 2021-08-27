# coding=utf-8

import glob
import unittest
from ddt import ddt, data, unpack
from provider.utils import base64_encode_string, bytes_decode, unicode_encode
import provider.email_provider as email_provider


class Recipient:
    pass


@ddt
class TestListEmailRecipients(unittest.TestCase):
    @data(
        {
            "email_list": "one@example.org",
            "expected": ["one@example.org"],
        },
        {
            "email_list": ["one@example.org"],
            "expected": ["one@example.org"],
        },
        {
            "email_list": ["one@example.org", "two@example.org"],
            "expected": ["one@example.org", "two@example.org"],
        },
    )
    def test_list_email_recipients(self, test_data):
        "test formating a list of email recipients"
        email_list = email_provider.list_email_recipients(test_data.get("email_list"))
        self.assertEqual(email_list, test_data.get("expected"))

    @data(
        (None, False),
        ({}, False),
        ({"e_mail": None}, False),
        ({"e_mail": ""}, False),
        ({"e_mail": "elife@example.org"}, True),
        (Recipient(), False),
    )
    @unpack
    def test_valid_valid_recipient(self, recipient, expected):
        self.assertEqual(email_provider.valid_recipient(recipient), expected)

    @data(
        (None, False),
    )
    @unpack
    def test_valid_valid_recipient_dict(self, recipient, expected):
        self.assertEqual(email_provider.valid_recipient_dict(recipient), expected)

    @data(
        (None, False),
        ("", False),
        ("elife@example.org", True),
    )
    @unpack
    def test_valid_valid_recipient_object(self, e_mail, expected):
        recipient = Recipient()
        setattr(recipient, "e_mail", e_mail)
        self.assertEqual(email_provider.valid_recipient_object(recipient), expected)

    def test_encode_filename_none(self):
        self.assertIsNone(email_provider.encode_filename(None))


@ddt
class TestEncodeFilename(unittest.TestCase):
    @data(
        "Bayés_35774.docx",
        u"Bayés_35774.docx",
        b"Bay\xc3\xa9s_35774.docx",
        bytes_decode(b"Bay\xc3\xa9s_35774.docx"),
        bytes_decode(b"Baye\xcc\x81s_35774.docx"),
    )
    def test_encode_filename(self, filename):
        """the encoded name for the examples will always be the same"""
        expected = "Bayés_35774.docx"
        self.assertEqual(email_provider.encode_filename(filename), expected)
        # an alternate way to illustrate the string comparison
        expected_also = unicode_encode(u"Bay\u00e9s_35774.docx")
        self.assertEqual(email_provider.encode_filename(filename), expected_also)


@ddt
class TestSimpleMessage(unittest.TestCase):
    @data(
        ("plain", 'Content-Type: text/plain; charset="utf-8"'),
        ("html", 'Content-Type: text/html; charset="utf-8"'),
    )
    @unpack
    def test_simple_message(self, subtype, expected_content_type):
        sender = "sender@example.org"
        recipient = "recipient@example.org"
        subject = "Email subject"
        body = "<p>Email body</p>"
        expected_fragments = []
        # note: boundary value is not constant so cannot compare with a fixture easily
        expected_fragments.append("Content-Type: multipart/mixed; boundary=")
        expected_fragments.append("Subject: %s" % subject)
        expected_fragments.append("From: %s" % sender)
        expected_fragments.append("To: %s" % recipient)

        expected_fragments.append(expected_content_type)
        expected_fragments.append("MIME-Version: 1.0")
        expected_fragments.append("Content-Transfer-Encoding: base64")
        # body is base64 encoded
        expected_fragments.append(base64_encode_string(body))
        # create the message
        email_message = email_provider.simple_message(
            sender, recipient, subject, body, subtype=subtype
        )
        for expected in expected_fragments:
            self.assertTrue(
                expected in str(email_message),
                "Fragment %s not found in email %s" % (expected, str(email_message)),
            )

    def test_simple_messages(self):
        "test creating multiple messages"
        sender = "sender@example.org"
        recipients = ["recipient_one@example.org", "recipient_two@example.org"]
        subject = "Email subject"
        body = "<p>Email body</p>"
        email_messages = email_provider.simple_messages(
            sender, recipients, subject, body
        )
        self.assertEqual(len(email_messages), 2)

    def test_simple_message_attachments(self):
        """test adding an email attachment to a message"""
        subtype = "html"
        sender = "sender@example.org"
        recipient = "recipient@example.org"
        subject = "Digest: Bayés_35774"
        body = "<p>Email body</p>"
        expected_fragments = []
        # workaround with file system name encoding, get the docx file name from disk
        for name in glob.glob("tests/fixtures/digests/*.docx"):
            if name.endswith("35774.docx"):
                attachment_file = name
        attachments = [attachment_file]
        # compare attachment in body
        expected_fragments.append(
            "Content-Disposition: attachment; filename*=utf-8''Bay%C3%A9s_35774.docx"
        )
        email_message = email_provider.simple_message(
            sender, recipient, subject, body, subtype=subtype, attachments=attachments
        )
        for expected in expected_fragments:
            self.assertTrue(
                expected in str(email_message),
                "Fragment %s not found in email %s" % (expected, str(email_message)),
            )

    def test_simple_email_body(self):
        datetime_string = "2019-08-21T16:00:13.000Z"
        body_content = "Body"
        expected = "Body\n\nAs at 2019-08-21T16:00:13.000Z\n\nSincerely\n\neLife bot"
        email_body = email_provider.simple_email_body(datetime_string, body_content)
        self.assertEqual(email_body, expected)


class TestAdminEmail(unittest.TestCase):
    def test_get_admin_email_body_foot(self):
        """test simple string Template rendering"""
        activity_id = "DepositCrossref"
        workflow_id = "DepositCrossref"
        datetime_string = "2019-08-21T16:00:13.000Z"
        domain = "Publish"
        email_body_foot = email_provider.get_admin_email_body_foot(
            activity_id, workflow_id, datetime_string, domain
        )
        self.assertTrue("SWF workflow details:" in email_body_foot)
        self.assertTrue(("activityId: %s" % activity_id) in email_body_foot)
        self.assertTrue(("As part of workflowId: %s" % workflow_id) in email_body_foot)
        self.assertTrue(("As at %s" % datetime_string) in email_body_foot)
        self.assertTrue(("Domain: %s" % domain) in email_body_foot)


class TestGetEmailSubject(unittest.TestCase):
    def test_get_email_subject(self):
        datetime_string = "2019-08-21T16:00:13.000Z"
        activity_status_text = "Success!"
        name = "DepositCrossref"
        domain = "Publish"
        outbox_s3_key_names = ["crossref/outbox/elife-00666-v1.xml"]
        expected = "%s %s files: 1, 2019-08-21T16:00:13.000Z, eLife SWF domain: %s" % (
            name,
            activity_status_text,
            domain,
        )
        email_subject = email_provider.get_email_subject(
            datetime_string, activity_status_text, name, domain, outbox_s3_key_names
        )
        self.assertEqual(email_subject, expected)


class TestGetEmailBodyHead(unittest.TestCase):
    def test_get_email_body_head_no_statuses(self):
        name = "DepositCrossref"
        activity_status_text = "Success!"
        statuses = {}
        expected = "DepositCrossref status:\n\nSuccess!\n\n\n"
        email_body_head = email_provider.get_email_body_head(
            name, activity_status_text, statuses
        )
        self.assertEqual(email_body_head, expected)

    def test_get_email_body_head_all_statuses(self):
        name = "DepositCrossref"
        activity_status_text = "Success!"
        statuses = {
            "unsupported_status_value": None,
            "activity": True,
            "generate": True,
            "approve": True,
            "upload": False,
            "publish": None,
            "outbox": None,
        }
        expected = (
            "DepositCrossref status:\n\n"
            "Success!\n\n"
            "activity_status: True\n"
            "generate_status: True\n"
            "approve_status: True\n"
            "upload_status: False\n"
            "publish_status: None\n"
            "outbox_status: None\n\n"
        )
        email_body_head = email_provider.get_email_body_head(
            name, activity_status_text, statuses
        )
        self.assertEqual(email_body_head, expected)


class TestGetEmailBodyMiddle(unittest.TestCase):
    def test_get_email_body_middle_no_outbox_files(self):
        activity_name = "crossref"
        outbox_s3_key_names = []
        published_file_names = []
        not_published_file_names = []
        http_detail_list = None
        expected = "\nOutbox files: \nNo files in outbox.\n"
        email_body_middle = email_provider.get_email_body_middle(
            activity_name,
            outbox_s3_key_names,
            published_file_names,
            not_published_file_names,
            http_detail_list,
        )
        self.assertEqual(email_body_middle, expected)

    def test_get_email_body_middle(self):
        activity_name = "crossref"
        outbox_s3_key_names = ["crossref/outbox/elife-00666-v1.xml"]
        published_file_names = ["elife-00777-v1.xml"]
        not_published_file_names = ["elife-99999-v1.xml"]
        http_detail_list = [
            "XML file: tmp/elife-crossref-00666.xml",
            "HTTP status: 200",
            "HTTP response: \n<html/>",
        ]
        expected = (
            "\nOutbox files: \n"
            "crossref/outbox/elife-00666-v1.xml\n\n"
            "Published files generated crossref XML: \nelife-00777-v1.xml\n\n"
            "Files not approved or failed crossref XML: \nelife-99999-v1.xml\n\n"
            "-------------------------------\n"
            "HTTP deposit details: \n"
            "XML file: tmp/elife-crossref-00666.xml\n"
            "HTTP status: 200\n"
            "HTTP response: \n<html/>\n"
        )
        email_body_middle = email_provider.get_email_body_middle(
            activity_name,
            outbox_s3_key_names,
            published_file_names,
            not_published_file_names,
            http_detail_list,
        )
        self.assertEqual(email_body_middle, expected)
