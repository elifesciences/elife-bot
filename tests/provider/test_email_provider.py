# coding=utf-8

import glob
import unittest
from ddt import ddt, data, unpack
from provider.utils import base64_encode_string, bytes_decode, unicode_encode
import provider.email_provider as email_provider


class Recipient(object):
    pass


@ddt
class TestListEmailRecipients(unittest.TestCase):

    @data(
        {
            "email_list": 'one@example.org',
            "expected": ['one@example.org'],
        },
        {
            "email_list": ['one@example.org'],
            "expected": ['one@example.org'],
        },
        {
            "email_list": ['one@example.org', 'two@example.org'],
            "expected": ['one@example.org', 'two@example.org'],
        },
        )
    def test_list_email_recipients(self, test_data):
        "test formating a list of email recipients"
        email_list = email_provider.list_email_recipients(test_data.get('email_list'))
        self.assertEqual(email_list, test_data.get('expected'))

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

    @data(
        'Bayés_35774.docx',
        u'Bayés_35774.docx',
        b'Bay\xc3\xa9s_35774.docx',
        bytes_decode(b'Bay\xc3\xa9s_35774.docx'),
        bytes_decode(b'Baye\xcc\x81s_35774.docx')
    )
    def test_encode_filename(self, filename):
        """the encoded name for the examples will always be the same"""
        expected = 'Bayés_35774.docx'
        self.assertEqual(email_provider.encode_filename(filename), expected)
        # an alternate way to illustrate the string comparison
        expected_also = unicode_encode(u'Bay\u00e9s_35774.docx')
        self.assertEqual(email_provider.encode_filename(filename), expected_also)

    @data(
        ('plain', 'Content-Type: text/plain; charset="utf-8"'),
        ('html', 'Content-Type: text/html; charset="utf-8"'),
    )
    @unpack
    def test_simple_message(self, subtype, expected_content_type):
        sender = 'sender@example.org'
        recipient = 'recipient@example.org'
        subject = 'Email subject'
        body = '<p>Email body</p>'
        expected_fragments = []
        # note: boundary value is not constant so cannot compare with a fixture easily
        expected_fragments.append('Content-Type: multipart/mixed; boundary=')
        expected_fragments.append('Subject: %s' % subject)
        expected_fragments.append('From: %s' % sender)
        expected_fragments.append('To: %s' % recipient)
        expected_fragments.append(expected_content_type)
        expected_fragments.append('MIME-Version: 1.0')
        expected_fragments.append('Content-Transfer-Encoding: base64')
        # body is base64 encoded
        expected_fragments.append(base64_encode_string(body))
        # create the message
        email_message = email_provider.simple_message(
            sender, recipient, subject, body, subtype=subtype)
        for expected in expected_fragments:
            self.assertTrue(
                expected in str(email_message),
                'Fragment %s not found in email %s' % (expected, str(email_message)))

    def test_simple_message_attachments(self):
        """test adding an email attachment to a message"""
        subtype = 'html'
        sender = 'sender@example.org'
        recipient = 'recipient@example.org'
        subject = 'Digest: Bayés_35774'
        body = '<p>Email body</p>'
        expected_fragments = []
        # workaround with file system name encoding, get the docx file name from disk
        for name in glob.glob('tests/fixtures/digests/*.docx'):
            if name.endswith("35774.docx"):
                attachment_file = name
        attachments = [attachment_file]
        # compare attachment in body
        expected_fragments.append("Content-Disposition: attachment; filename*=utf-8''Bay%C3%A9s_35774.docx")
        email_message = email_provider.simple_message(
            sender, recipient, subject, body, subtype=subtype, attachments=attachments)
        for expected in expected_fragments:
            self.assertTrue(
                expected in str(email_message),
                'Fragment %s not found in email %s' % (expected, str(email_message)))


    def test_get_admin_email_body_foot(self):
        """test simple string Template rendering"""
        activity_id = 'DepositCrossref'
        workflow_id = 'DepositCrossref'
        datetime_string = '2019-08-21T16:00:13.000Z'
        domain = 'Publish'
        email_body_foot = email_provider.get_admin_email_body_foot(
            activity_id, workflow_id, datetime_string, domain)
        self.assertTrue('SWF workflow details:' in email_body_foot)
        self.assertTrue(('activityId: %s' % activity_id) in email_body_foot)
        self.assertTrue(('As part of workflowId: %s' % workflow_id) in email_body_foot)
        self.assertTrue(('As at %s' % datetime_string) in email_body_foot)
        self.assertTrue(('Domain: %s' % domain) in email_body_foot)
