# coding=utf-8

import unittest
from ddt import ddt, data, unpack
from provider.utils import base64_encode_string, unicode_encode
import provider.email_provider as email_provider
from tests import fixture_file


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
        attachment_file = fixture_file(unicode_encode('Bayés_35774.docx'), 'digests')
        attachments = [attachment_file]
        # compare two fragments because in Python 2 it wraps with extra quotation marks
        expected_fragments.append("Content-Disposition: attachment; filename*=")
        expected_fragments.append("utf-8''Baye%CC%81s_35774.docx")
        # create the message
        email_message = email_provider.simple_message(
            sender, recipient, subject, body, subtype=subtype, attachments=attachments)
        for expected in expected_fragments:
            self.assertTrue(
                expected in str(email_message),
                'Fragment %s not found in email %s' % (expected, str(email_message)))
