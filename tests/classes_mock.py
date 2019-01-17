import time
import os
from datetime import datetime

class FakeBotoConnection:
    def start_workflow_execution(self, *args):
        pass

class FakeLayer1:
    def respond_decision_task_completed(self, task_token, decisions=None, execution_context=None):
        pass

    def start_workflow_execution(
        self, domain, workflow_id, workflow_name, workflow_version, task_list=None, 
        child_policy=None, execution_start_to_close_timeout=None, input=None, 
        tag_list=None, task_start_to_close_timeout=None):
        pass

    def list_closed_workflow_executions(
        self, domain, start_latest_date=None, start_oldest_date=None, close_latest_date=None, 
        close_oldest_date=None, close_status=None, tag=None, workflow_id=None, workflow_name=None, 
        workflow_version=None, maximum_page_size=None, next_page_token=None, reverse_order=None):
        return {'executionInfos': []}

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


class FakeSMTPServer():

    def __init__(self, tmp_dir):
        self.number = 0
        self.tmp_dir = tmp_dir

    def sendmail(self, sender, recipient, message):
        self.process_message(None, sender, recipient, message)

    def process_message(self, peer, mailfrom, rcpttos, data):
        filename = os.path.join(
            self.tmp_dir,
            '%s-%d.eml' % (datetime.now().strftime('%Y%m%d%H%M%S'), self.number))
        with open(filename, 'w') as open_file:
            open_file.write(data)
        self.number += 1
