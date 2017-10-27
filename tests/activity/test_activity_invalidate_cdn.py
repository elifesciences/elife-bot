import unittest
from activity.activity_InvalidateCdn import activity_InvalidateCdn
from boto.cloudfront.exception import CloudFrontServerError
import settings_mock
from classes_mock import FakeLogger
from mock import patch, call

activity_data = {
                    "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
                    "article_id": "00353",
                    "version": "1"
                }

class TestInvalidateCdn(unittest.TestCase):

    def setUp(self):
        self.invalidatecdn = activity_InvalidateCdn(settings_mock, None, None, None, None)
        self.invalidatecdn.logger = FakeLogger()

    @patch('provider.cloudfront_provider.create_invalidation')
    @patch.object(activity_InvalidateCdn, 'emit_monitor_event')
    def test_invalidation_success(self, fake_emit, invalidation_mock):
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_SUCCESS)

    @patch('provider.cloudfront_provider.create_invalidation')
    @patch.object(activity_InvalidateCdn, 'emit_monitor_event')
    def test_invalidation_permanent_failure(self, fake_emit, invalidation_mock):
        invalidation_mock.side_effect = Exception("An error occurred")
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_PERMANENT_FAILURE)

    @patch('provider.cloudfront_provider.create_invalidation')
    @patch.object(activity_InvalidateCdn, 'emit_monitor_event')
    def test_invalidation_temporary_failure_due_to_rate_limiting(self, fake_emit, invalidation_mock):
        invalidation_mock.side_effect = CloudFrontServerError(400, 'Bad Request', '<ErrorResponse xmlns="http://cloudfront.amazonaws.com/doc/2010-11-01/"><Error><Type>Sender</Type><Code>TooManyInvalidationsInProgress</Code><Message>Processing your request will cause you to exceed the maximum number of in-progress wildcard invalidations.</Message></Error><RequestId>b47186e6-b7d7-11e7-bd6c-d7fe045b879d</RequestId></ErrorResponse>')
        result = self.invalidatecdn.do_activity(activity_data)
        self.assertEqual(result, self.invalidatecdn.ACTIVITY_TEMPORARY_FAILURE)


if __name__ == '__main__':
    unittest.main()
