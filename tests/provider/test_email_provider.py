import unittest
from ddt import ddt, data
import provider.email_provider as email_provider


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
