import time

class FakeBotoConnection:
    def start_workflow_execution(self, *args):
        pass

class FakeFlag():
    "a fake object to return process monitoring status"
    def __init__(self, timeout_seconds=1):
        self.timeout_seconds = timeout_seconds
        self.green_value = True

    def green(self):
        "first return True, second call return False after waiting timeout_seconds"
        return_value = self.green_value
        self.green_value = False
        # return immediately when returning True, wait before return False
        if return_value is False:
            time.sleep(self.timeout_seconds)
        return return_value

class FakeS3Event():
    "object to test an S3 notification event from an SQS queue"
    def __init__(self):
        self.notification_type = 'S3Event'
        self.id = None
        # test data below
        self._event_name = u'ObjectCreated:Put'
        self._event_time = u'2016-07-28T16:14:27.809576Z'
        self._bucket_name =  u'jen-elife-production-final'
        self._file_name =  u'elife-00353-vor-r1.zip'
        self._file_etag = u'e7f639f63171c097d4761e2d2efe8dc4'
        self._file_size = 1097506
    def event_name(self):
        return self._event_name
    def event_time(self):
        return self._event_time
    def bucket_name(self):
        return self._bucket_name
    def file_name(self):
        return self._file_name
    def file_etag(self):
        return self._file_etag
    def file_size(self):
        return self._file_size
