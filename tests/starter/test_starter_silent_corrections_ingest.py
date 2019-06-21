import unittest
from ddt import ddt, data
from mock import patch
import starter.starter_SilentCorrectionsIngest as starter_module
from starter.starter_SilentCorrectionsIngest import starter_SilentCorrectionsIngest
from starter.starter_helper import NullRequiredDataException
from S3utility.s3_notification_info import S3NotificationInfo
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.classes_mock import FakeBotoConnection
from tests.activity.classes_mock import FakeLogger

RUN_EXAMPLE = u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda'


@ddt
class TestStarterSilentCorrectionsIngest(unittest.TestCase):
    def setUp(self):
        self.starter_silent_corrections_ingest = starter_SilentCorrectionsIngest()

    def test_silent_corrections_ingest_starter_no_article(self):
        self.assertRaises(NullRequiredDataException, self.starter_silent_corrections_ingest.start,
                          settings=settings_mock, run=RUN_EXAMPLE, info=test_data.data_error_lax)

    @patch('starter.starter_helper.get_starter_logger')
    @patch('boto.swf.layer1.Layer1')
    def test_silent_corrections_ingest_starter_(self, fake_boto_conn, fake_logger):
        fake_logger.return_value = FakeLogger()
        fake_boto_conn.return_value = FakeBotoConnection()
        self.starter_silent_corrections_ingest.start(
            settings=settings_mock, run=RUN_EXAMPLE,
            info=S3NotificationInfo.from_dict(test_data.silent_ingest_article_zip_data))
