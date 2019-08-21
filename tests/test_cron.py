import unittest
import sys
import datetime
from pytz import timezone
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

    def test_console_start(self):
        env = 'foo'
        expected = env
        testargs = ['cron.py', '-e', env]
        with patch.object(sys, 'argv', testargs):
            self.assertEqual(cron.console_start(), expected)

    def test_console_start_blank(self):
        expected = 'dev'
        testargs = ['cron.py']
        with patch.object(sys, 'argv', testargs):
            self.assertEqual(cron.console_start(), expected)

    def test_get_current_datetime(self):
        self.assertIsNotNone(cron.get_current_datetime())

    @patch.object(cron, 'start_workflow')
    @patch.object(cron, 'get_current_datetime')
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
    def test_run_cron(self, date_time, fake_workflow_start, fake_get_current_datetime,
                      fake_start_workflow):
        fake_workflow_start.return_value = True
        fake_start_workflow.return_value = None
        fake_get_current_datetime.return_value = datetime.datetime.strptime(
            date_time, '%Y-%m-%d %H:%M:%S')
        self.assertIsNone(cron.run_cron(settings_mock))

    @patch("provider.swfmeta.SWFMeta.get_last_completed_workflow_execution_startTimestamp")
    @data(
        {
            "workflow_id": None
        },
        {
            "workflow_id": "S3Monitor"
        },
        {
            "workflow_id": "S3Monitor_POA"
        },
        {
            "workflow_id": None
        },
        {
            "workflow_id": "PubRouterDeposit_HEFCE"
        },
        {
            "workflow_id": None
        },
    )
    def test_workflow_conditional_start(self, test_data, fake_timestamp):
        fake_timestamp.return_value = 0
        workflow_id = test_data.get("workflow_id")
        start_seconds = 0
        self.assertTrue(cron.workflow_conditional_start(
            settings_mock, start_seconds, workflow_id=workflow_id))

    @patch.object(cron, 'get_s3_key_names_from_bucket')
    @patch.object(FakeS3Connection, 'lookup')
    @patch.object(cron, 'S3Connection')
    @patch.object(FakeLayer1, 'start_workflow_execution')
    @patch('boto.swf.layer1.Layer1')
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
    def test_start_workflow(self, test_data, fake_conn, fake_start,
                            fake_s3_mock, fake_lookup, fake_s3_key_names):
        fake_conn.return_value = FakeLayer1()
        fake_start.return_value = {}
        fake_s3_mock.return_value = FakeS3Connection()
        fake_lookup.return_value = FakeBucket()
        fake_s3_key_names.return_value = ['foo']
        starter_name = test_data.get("starter_name")
        workflow_id = test_data.get("workflow_id")
        start_seconds = 0
        self.assertIsNone(cron.start_workflow(settings_mock, starter_name, workflow_id))

    @patch.object(FakeBucket, 'list')
    def test_get_s3_key_names_from_bucket(self, fake_list):
        key_name = '00003/file.zip'
        fake_bucket = FakeBucket()
        fake_key = Key(fake_bucket, '00003/file.zip')
        fake_list.return_value = [fake_key]
        s3_key_names = cron.get_s3_key_names_from_bucket(fake_bucket)
        self.assertEqual(s3_key_names, [key_name])


@ddt
class TestGetLocalDatetime(unittest.TestCase):

    @data(
        {
            "comment": "BST Summer August 2019",
            "date_time": "2019-08-19 10:00:00 UTC",
            "timezone": "Europe/London",
            "expected_date_time": "2019-08-19 11:00:00"
        },
        {
            "comment": "Changes to GMT October 27 2019",
            "date_time": "2019-10-27 10:00:00 UTC",
            "timezone": "Europe/London",
            "expected_date_time": "2019-10-27 10:00:00"
        }
    )
    def test_get_local_datetime(self, test_data):
        pytz_timezone = timezone(test_data.get("timezone"))
        datetime_object = datetime.datetime.strptime(
            test_data.get("date_time"), '%Y-%m-%d %H:%M:%S %Z')
        expected_datetime = datetime.datetime.strptime(
            test_data.get("expected_date_time"), '%Y-%m-%d %H:%M:%S')
        new_datetime = cron.get_local_datetime(datetime_object, pytz_timezone)
        self.assertEqual(new_datetime, expected_datetime)


@ddt
class TestConditionalStarts(unittest.TestCase):

    def conditional_start_test_run(self, test_data):
        """logic for calling conditional_starts() for reuse in test scenarios"""
        current_datetime = datetime.datetime.strptime(
            test_data.get("date_time"), '%Y-%m-%d %H:%M:%S %Z')
        conditional_start_list = cron.conditional_starts(current_datetime)
        starter_names = [value.get("starter_name") for value in conditional_start_list]
        workflow_ids = [value.get("workflow_id") for value in conditional_start_list]
        self.assertEqual(
            starter_names, test_data.get("expected_starter_names"),
            'failed in scenario {comment}'.format(comment=test_data.get("comment")))
        self.assertEqual(
            workflow_ids, test_data.get("expected_workflow_ids"),
            'failed in scenario {comment}'.format(comment=test_data.get("comment")))

    @data(
        {
            "comment": "zero hour",
            "date_time": "1970-01-01 00:00:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_DepositCrossref"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "DepositCrossref"
            ]
        }
    )
    def test_conditional_starts_00_00(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "half past midnight",
            "date_time": "1970-01-01 00:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_S3Monitor"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "S3Monitor_POA"
            ]
        }
    )
    def test_conditional_starts_00_30(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "10:45 UTC",
            "date_time": "1970-01-01 10:45:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "cron_NewS3POA",
                "starter_PubmedArticleDeposit",
                "starter_AdminEmail"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "cron_NewS3POA",
                "PubmedArticleDeposit",
                "AdminEmail"
            ]
        },
    )
    def test_conditional_starts_10_45_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "2019-08-19 11:30 UTC",
            "date_time": "2019-08-19 11:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PublishPOA",
                "starter_S3Monitor"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PublishPOA",
                "S3Monitor_POA"
            ]
        },
    )
    def test_conditional_starts_11_30_utc_august(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "2019-10-27 12:30 UTC",
            "date_time": "2019-10-27 12:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PublishPOA",
                "starter_S3Monitor"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PublishPOA",
                "S3Monitor_POA"
            ]
        },
    )
    def test_conditional_starts_12_30_utc_october_27_2019(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "17:45 UTC",
            "date_time": "1970-01-01 17:45:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PublicationEmail",
                "starter_PubmedArticleDeposit",
                "starter_AdminEmail"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PublicationEmail",
                "PubmedArticleDeposit",
                "AdminEmail"
            ]
        },
    )
    def test_conditional_starts_17_45_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "20:30 UTC",
            "date_time": "1970-01-01 20:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_S3Monitor",
                "starter_PubRouterDeposit"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "S3Monitor_POA",
                "PubRouterDeposit_PMC"
            ]
        },
    )
    def test_conditional_starts_20_30_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "21:30 UTC",
            "date_time": "1970-01-01 21:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_S3Monitor",
                "starter_PubRouterDeposit"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "S3Monitor_POA",
                "PubRouterDeposit_WoS"
            ]
        },
    )
    def test_conditional_starts_21_30_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "21:45 UTC",
            "date_time": "1970-01-01 21:45:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PubRouterDeposit",
                "starter_PubmedArticleDeposit",
                "starter_AdminEmail"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PubRouterDeposit_GoOA",
                "PubmedArticleDeposit",
                "AdminEmail"
            ]
        },
    )
    def test_conditional_starts_21_45_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "22:30 UTC",
            "date_time": "1970-01-01 22:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_S3Monitor",
                "starter_PubRouterDeposit"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "S3Monitor_POA",
                "PubRouterDeposit_Scopus"
            ]
        },
    )
    def test_conditional_starts_22_30_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "22:45 UTC",
            "date_time": "1970-01-01 22:45:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PubRouterDeposit",
                "starter_PubmedArticleDeposit",
                "starter_AdminEmail"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PubRouterDeposit_Cengage",
                "PubmedArticleDeposit",
                "AdminEmail"
            ]
        },
    )
    def test_conditional_starts_22_45_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "23:00 UTC",
            "date_time": "1970-01-01 23:00:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_DepositCrossref",
                "starter_PubRouterDeposit"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "DepositCrossref",
                "PubRouterDeposit_CNKI"
            ]
        },
    )
    def test_conditional_starts_23_00_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "23:30 UTC",
            "date_time": "1970-01-01 23:30:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_S3Monitor",
                "starter_PubRouterDeposit"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "S3Monitor_POA",
                "PubRouterDeposit_CNPIEC"
            ]
        },
    )
    def test_conditional_starts_23_30_utc(self, test_data):
        self.conditional_start_test_run(test_data)

    @data(
        {
            "comment": "23:45 UTC",
            "date_time": "1970-01-01 23:45:00 UTC",
            "expected_starter_names": [
                "cron_FiveMinute",
                "starter_PubRouterDeposit",
                "starter_PubmedArticleDeposit",
                "starter_AdminEmail"
            ],
            "expected_workflow_ids": [
                "cron_FiveMinute",
                "PubRouterDeposit_HEFCE",
                "PubmedArticleDeposit",
                "AdminEmail"
            ]
        },
    )
    def test_conditional_starts_23_45_utc(self, test_data):
        self.conditional_start_test_run(test_data)


if __name__ == '__main__':
    unittest.main()
