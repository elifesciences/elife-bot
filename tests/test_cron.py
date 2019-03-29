import unittest
import time
from ddt import ddt, data
from mock import patch
from boto.s3.key import Key
import tests.settings_mock as settings_mock
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeS3Connection, FakeBucket
import cron


@ddt
class TestCron(unittest.TestCase):
    def setUp(self):
        pass

    @patch.object(time, 'gmtime')
    @patch.object(cron, 'workflow_conditional_start')
    @data(
        "1970-01-01 10:45:00",
        "1970-01-01 11:45:00",
        "1970-01-01 16:45:00",
        "1970-01-01 17:45:00",
        "1970-01-01 12:30:00",
        "1970-01-01 20:30:00",
        "1970-01-01 21:30:00",
        "1970-01-01 21:45:00",
        "1970-01-01 22:30:00",
        "1970-01-01 22:45:00",
        "1970-01-01 23:00:00",
        "1970-01-01 23:30:00",
        "1970-01-01 23:45:00",
    )
    def test_run_cron(self, date_time, fake_workflow_start, fake_gmtime):
        fake_gmtime.return_value = time.strptime(date_time, '%Y-%m-%d %H:%M:%S')
        self.assertIsNone(cron.run_cron(settings_mock))

    @patch.object(cron, 'get_s3_key_names_from_bucket')
    @patch.object(FakeS3Connection, 'lookup')
    @patch.object(cron, 'S3Connection')
    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
    @patch("provider.swfmeta.SWFMeta.get_last_completed_workflow_execution_startTimestamp")
    @data(
        {
            "starter_name": "starter_AdminEmail",
            "workflow_id": None
        },
        {
            "starter_name": "starter_S3Monitor",
            "workflow_id": "S3Monitor"
        },
        {
            "starter_name": "starter_S3Monitor",
            "workflow_id": "S3Monitor_POA"
        },
        {
            "starter_name": "starter_PubmedArticleDeposit",
            "workflow_id": None
        },
        {
            "starter_name": "starter_PubRouterDeposit",
            "workflow_id": "PubRouterDeposit_HEFCE"
        },
        {
            "starter_name": "starter_PublishPOA",
            "workflow_id": None
        },
    )
    def test_workflow_conditional_start(self, test_data, fake_timestamp, fake_conn, fake_start,
                                        fake_s3_mock, fake_lookup, fake_s3_key_names):
        fake_timestamp.return_value = 0
        fake_conn.return_value = FakeLayer1()
        fake_start.return_value = {}
        fake_s3_mock.return_value = FakeS3Connection()
        fake_lookup.return_value = FakeBucket()
        fake_s3_key_names.return_value = ['foo']
        starter_name = test_data.get("starter_name")
        workflow_id = test_data.get("workflow_id")
        start_seconds = 0
        self.assertIsNone(cron.workflow_conditional_start(
            settings_mock, starter_name, start_seconds, workflow_id=workflow_id))

    @patch.object(FakeBucket, 'list')
    def test_get_s3_key_names_from_bucket(self, fake_list):
        key_name = '00003/file.zip'
        fake_bucket = FakeBucket()
        fake_key = Key(fake_bucket, '00003/file.zip')
        fake_list.return_value = [fake_key]
        s3_key_names = cron.get_s3_key_names_from_bucket(fake_bucket)
        self.assertEqual(s3_key_names, [key_name])


if __name__ == '__main__':
    unittest.main()
