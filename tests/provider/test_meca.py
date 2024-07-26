import unittest
import os
from mock import patch
from testfixtures import TempDirectory
from provider import meca
from tests import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeSession


class TestMecaFileName(unittest.TestCase):
    "tests for meca_file_name()"

    def test_meca_file_name(self):
        article_id = 95901
        version = "1"
        expected = "95901-v1-meca.zip"
        result = meca.meca_file_name(article_id, version)
        self.assertEqual(result, expected)


class TestPostXmlFile(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        start_xml = b"<root/>"
        self.transformed_xml = b"<root>Modified.</root>"
        self.file_path = os.path.join(self.directory.path, "file.xml")
        with open(self.file_path, "wb") as open_file:
            open_file.write(start_xml)

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.post")
    def test_post_xml_file(self, fake_post):
        "test post_xml_file()"
        status_code = 200
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        result = meca.post_xml_file(
            self.file_path,
            settings_mock.meca_dtd_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, self.transformed_xml)

    @patch("requests.post")
    def test_status_code_400(self, fake_post):
        "test response status_code 400"
        status_code = 400
        logger = FakeLogger()
        fake_post.return_value = FakeResponse(status_code, content=self.transformed_xml)
        with self.assertRaises(Exception):
            meca.post_xml_file(
                self.file_path,
                settings_mock.meca_xsl_endpoint,
                settings_mock.user_agent,
                "test",
                logger,
            )

    @patch("requests.post")
    def test_bad_response(self, fake_post):
        "test if response content is None"
        logger = FakeLogger()
        fake_post.return_value = None
        result = meca.post_xml_file(
            self.file_path,
            settings_mock.meca_xsl_endpoint,
            settings_mock.user_agent,
            "test",
            logger,
        )
        self.assertEqual(result, None)


class TesetPostToEndpoint(unittest.TestCase):
    "tests for post_to_endpoint()"

    def setUp(self):
        self.xml_file_path = "article.xml"
        self.endpoint_url = settings_mock.meca_dtd_endpoint
        self.caller_name = "ValidateJatsDtd"

    @patch.object(meca, "post_xml_file")
    def test_post_to_endpoint(self, fake_post_xml_file):
        "test normal response content returned"
        logger = FakeLogger()
        response_content = b""
        fake_post_xml_file.return_value = response_content
        result = meca.post_to_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        self.assertEqual(result, response_content)

    @patch.object(meca, "post_xml_file")
    def test_exception(self, fake_post_xml_file):
        "test exception raised"
        logger = FakeLogger()
        fake_post_xml_file.side_effect = Exception("An exception")
        result = meca.post_to_endpoint(
            self.xml_file_path, self.endpoint_url, None, self.caller_name, logger
        )
        self.assertEqual(result, None)
        self.assertEqual(
            logger.logexception,
            "%s, posting %s to endpoint %s: An exception"
            % (self.caller_name, self.xml_file_path, self.endpoint_url),
        )


class TestLogToSession(unittest.TestCase):
    "tests for log_to_session()"

    def test_add_log_messages(self):
        "test adding new log_messages key to the session"
        mock_session = FakeSession({})
        log_message = "A log message"
        # invoke
        meca.log_to_session(log_message, mock_session)
        self.assertEqual(mock_session.get_value("log_messages"), log_message)

    def test_append_log_messages(self):
        "test appending a log_message to existing log_messages in the session"
        log_messages = "First log message."
        mock_session = FakeSession({"log_messages": log_messages})
        log_message = "A log message"
        # invoke
        meca.log_to_session(log_message, mock_session)
        self.assertEqual(
            mock_session.get_value("log_messages"), "%s%s" % (log_messages, log_message)
        )
