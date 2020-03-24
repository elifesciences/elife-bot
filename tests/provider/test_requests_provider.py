import unittest
from collections import OrderedDict
from mock import patch
from requests.exceptions import HTTPError
from digestparser.objects import Digest
from provider import requests_provider, digest_provider
from provider.utils import bytes_decode
from tests.activity.classes_mock import FakeLogger, FakeResponse
import tests.activity.helpers as helpers


class TestRequestsProvider(unittest.TestCase):

    def test_jats_post_params(self):
        api_key = 'key'
        account_key = '1'
        expected = OrderedDict([
            ('apiKey', api_key),
            ('accountKey', account_key),
        ])
        result = requests_provider.jats_post_params(api_key, account_key)
        self.assertEqual(result, expected)

    def test_jats_post_payload(self):
        content_type = 'decision'
        doi = '10.7554/eLife.00666'
        content = {}
        api_key = 'key'
        account_key = '1'

        expected = OrderedDict([
            ('apiKey', api_key),
            ('accountKey', account_key),
            ('doi', doi),
            ('type', content_type),
            ('content', {})
        ])
        result = requests_provider.jats_post_payload(
            content_type, doi, content, api_key, account_key)
        self.assertEqual(result, expected)


class TestRequestsProviderPostAs(unittest.TestCase):

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_get_as_params(self, fake_connection):
        """"test get data as params only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url + '?type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        expected_body = None
        # populate the fake request
        resp = requests_provider.get_as_params(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_params(self, fake_connection):
        """"test posting data as params only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url + '?type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        expected_body = None
        # populate the fake request
        resp = requests_provider.post_as_params(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_data(self, fake_connection):
        """"test posting data as data only"""
        url = 'http://localhost/'
        api_key = 'key'
        account_key = '1'
        content_type = 'application/xml'
        params = OrderedDict([
            ("apiKey", api_key),
            ("accountKey", account_key)
        ])
        headers = {'Content-Type': content_type}
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = '%s?apiKey=%s&accountKey=%s' % (url, api_key, account_key)
        expected_body = 'type=digest&content=%3Cp%3E%2298%25%22%CE%B2%3C%2Fp%3E'
        # populate the fake request
        resp = requests_provider.post_as_data(url, payload, params, headers)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(resp.request.body, expected_body)
        self.assertEqual(resp.request.headers.get('Content-Type'), content_type)

    @patch('requests.adapters.HTTPAdapter.get_connection')
    def test_post_as_json(self, fake_connection):
        """test posting data as data only"""
        url = 'http://localhost/'
        payload = OrderedDict([
            ("type", "digest"),
            ("content", '<p>"98%"β</p>')
            ])
        expected_url = url
        expected_body = '{"type": "digest", "content": "<p>\\"98%\\"\\u03b2</p>"}'
        # populate the fake request
        resp = requests_provider.post_as_json(url, payload)
        # make assertions
        self.assertEqual(resp.request.url, expected_url)
        self.assertEqual(bytes_decode(resp.request.body), expected_body)


class TestRequestsProviderPost(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    @patch('requests.post')
    def test_post_to_endpoint_200(self, post_mock):
        post_mock.return_value = FakeResponse(200, {})
        url = ''
        payload = {}
        identifier = 'test'
        requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        # assert no errors or exceptions in log
        self.assertEqual(self.fake_logger.logerror, 'First logger error')
        self.assertEqual(self.fake_logger.logexception, 'First logger exception')

    @patch('requests.post')
    def test_post_to_endpoint_404(self, post_mock):
        post_mock.return_value = FakeResponse(404, {})
        url = ''
        payload = {}
        identifier = 'test'
        with self.assertRaises(HTTPError):
            requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertEqual(
            self.fake_logger.logerror,
            ('Error posting test to endpoint : status_code: 404\nrequest headers: {}\n' +
             'request body: None\nresponse headers: {}\nresponse: None\npayload: {}'))

    @patch('requests.post')
    def test_post_to_endpoint_exception(self, post_mock):
        post_mock.side_effect = Exception('Unknown exception')
        url = ''
        payload = {}
        identifier = 'test'
        with self.assertRaises(Exception):
            requests_provider.post_to_endpoint(url, payload, self.fake_logger, identifier)
        self.assertEqual(
            self.fake_logger.logexception,
            'Exception in post_to_endpoint')


class TestEmailSubject(unittest.TestCase):

    def test_success_email_subject_msid_author(self):
        """email subject line with correct, unicode data"""
        digest_content = helpers.create_digest(u'Nö', '10.7554/eLife.99999')
        identity = 'Digest '
        msid = digest_provider.get_digest_msid(digest_content)
        expected = u'Digest JATS posted for article 99999, author Nö'
        subject = requests_provider.success_email_subject_msid_author(
            identity, msid, digest_content.author)
        self.assertEqual(subject, expected)

    def test_success_email_subject_digest_no_doi(self):
        """email subject line when no doi attribute"""
        digest_content = Digest()
        identity = 'Digest '
        msid = digest_provider.get_digest_msid(digest_content)
        expected = u'Digest JATS posted for article 0None, author None'
        file_name = requests_provider.success_email_subject_msid_author(
            identity, msid, digest_content.author)
        self.assertEqual(file_name, expected)

    def test_error_email_subject_msid_author(self):
        """error email subject"""
        digest_content = helpers.create_digest(u'Nö', '10.7554/eLife.99999')
        identity = 'digest'
        msid = digest_provider.get_digest_msid(digest_content)
        expected = u'Error in digest JATS post for article 99999, author Nö'
        subject = requests_provider.error_email_subject_msid_author(
            identity, msid, digest_content.author)
        self.assertEqual(subject, expected)

    def test_success_email_subject_doi(self):
        """email subject line using doi"""
        doi = '10.7554/eLife.99999'
        identity = 'Decision letter '
        expected = u'Decision letter JATS posted for article 10.7554/eLife.99999'
        subject = requests_provider.success_email_subject_doi(
            identity, doi)
        self.assertEqual(subject, expected)

    def test_error_email_subject_doi(self):
        """email subject line using doi"""
        doi = '10.7554/eLife.99999'
        identity = 'decision letter'
        expected = u'Error in decision letter JATS post for article 10.7554/eLife.99999'
        subject = requests_provider.error_email_subject_doi(
            identity, doi)
        self.assertEqual(subject, expected)


class TestEmailBody(unittest.TestCase):

    def test_success_email_body_content(self):
        """email body line with correct, unicode data"""
        digest_content = helpers.create_digest(u'Nö', '10.7554/eLife.99999')
        digest_content.text = [u'<i>First</i> paragraph.', u'<b>First</b> > second, nö?.']
        jats_content = digest_provider.digest_jats(digest_content)

        expected = u'''JATS content for article 10.7554/eLife.99999:

<p><italic>First</italic> paragraph.</p><p><bold>First</bold> &gt; second, nö?.</p>

'''
        body = requests_provider.success_email_body_content(digest_content.doi, jats_content)
        self.assertEqual(body, expected)

    def test_error_email_body_content(self):
        """email error body"""
        error_message = "Exception blah blah blah"
        digest_content = helpers.create_digest(u'Nö', '10.7554/eLife.99999')
        digest_content.text = [u'<i>First</i> paragraph.', u'<b>First</b> > second, nö?.']
        jats_content = digest_provider.digest_jats(digest_content)

        expected = u'''Exception blah blah blah

More details about the error may be found in the worker.log file

Article DOI: 10.7554/eLife.99999

JATS content: <p><italic>First</italic> paragraph.</p><p><bold>First</bold> &gt; second, nö?.</p>

'''
        body = requests_provider.error_email_body_content(
            digest_content.doi, jats_content, error_message)
        self.assertEqual(body, expected)
