import unittest
from ddt import ddt, data, unpack
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
