import time
import os
import ftplib
from datetime import datetime


class FakeBotoConnection:
    def __init__(self):
        self.start_called = None

    def start_workflow_execution(self, *args, **kwargs):
        self.start_called = True


class FakeSWFUnknownResourceFault(Exception):
    pass


class FakeSWFClientExceptions:
    def __init__(self):
        self.UnknownResourceFault = FakeSWFUnknownResourceFault()


class FakeSWFClient:
    def __init__(self, *args, **kwargs):
        # infos is JSON format infos in SWF format for workflow executions
        self.infos = []
        self.infos_counter = 0
        self.exceptions = FakeSWFClientExceptions()

    def add_infos(self, infos):
        "add an infos, to allow it to return more than one infos in succession"
        self.infos.append(infos)

    def list_open_workflow_executions(
        self,
        domain=None,
        startTimeFilter=None,
        executionFilter=None,
        typeFilter=None,
        closeStatusFilter=None,
        maximumPageSize=None,
        nextPageToken=None,
    ):
        """
        return the infos for testing, when testing the next_page_token and
        mocking the return values the final infos value needs not have a
        nextPageToken otherwise it will loop forever in some swfmeta functions
        """
        if len(self.infos) > 1:
            return_infos = self.infos[self.infos_counter]
            if self.infos_counter < len(self.infos) - 1:
                self.infos_counter = self.infos_counter + 1
            else:
                self.infos_counter = 0
            return return_infos
        else:
            # reset the counter self.infos_counter then return
            self.infos_counter = 0
            return self.infos[self.infos_counter]

    def list_closed_workflow_executions(
        self,
        domain=None,
        startTimeFilter=None,
        executionFilter=None,
        typeFilter=None,
        closeStatusFilter=None,
        maximumPageSize=None,
        nextPageToken=None,
    ):
        "for testing piggy-back list_open_workflow_executions to return infos"
        return self.list_open_workflow_executions()

    def count_closed_workflow_executions(
        self,
        domain=None,
        startTimeFilter=None,
        executionFilter=None,
        typeFilter=None,
        closeStatusFilter=None,
        maximumPageSize=None,
        nextPageToken=None,
    ):
        "for testing return a count of infos"
        count = 0
        infos = self.list_open_workflow_executions()
        if infos and infos.get("executionInfos"):
            count = len(infos.get("executionInfos"))
        return {"count": count, "truncated": False}

    def describe_workflow_type(self, domain, workflowType):
        pass

    def register_workflow_type(self, **kwargs):
        pass

    def describe_activity_type(self, domain, activityType):
        pass

    def register_activity_type(self, **kwargs):
        pass

    def poll_for_decision_task(self, **kwargs):
        pass

    def respond_decision_task_completed(self, taskToken, decisions=None):
        pass


class FakeLayer1:
    def respond_decision_task_completed(
        self, task_token, decisions=None, execution_context=None
    ):
        pass

    def start_workflow_execution(
        self,
        domain,
        workflow_id,
        workflow_name,
        workflow_version,
        task_list=None,
        child_policy=None,
        execution_start_to_close_timeout=None,
        input=None,
        tag_list=None,
        task_start_to_close_timeout=None,
    ):
        pass

    def list_closed_workflow_executions(
        self,
        domain,
        start_latest_date=None,
        start_oldest_date=None,
        close_latest_date=None,
        close_oldest_date=None,
        close_status=None,
        tag=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        maximum_page_size=None,
        next_page_token=None,
        reverse_order=None,
    ):
        return {"executionInfos": []}

    def describe_workflow_type(self, domain, workflow_name, workflow_version):
        pass

    def register_workflow_type(
        self,
        domain,
        name,
        version,
        task_list=None,
        default_child_policy=None,
        default_execution_start_to_close_timeout=None,
        default_task_start_to_close_timeout=None,
        description=None,
    ):
        pass

    def describe_activity_type(self, domain, activity_name, activity_version):
        pass

    def register_activity_type(
        self,
        domain,
        name,
        version,
        task_list=None,
        default_task_heartbeat_timeout=None,
        default_task_schedule_to_close_timeout=None,
        default_task_schedule_to_start_timeout=None,
        default_task_start_to_close_timeout=None,
        description=None,
    ):
        pass

    def poll_for_decision_task(
        domain, task_list, identity, maximum_page_size, next_page_token=None
    ):
        pass


class FakeFlag:
    "a fake object to return process monitoring status"

    def __init__(self, timeout_seconds=0.1):
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


class FakeS3Event:
    "object to test an S3 notification event from an SQS queue"

    def __init__(self, bucket_name=None):
        self.notification_type = "S3Event"
        self.id = None
        self.body = ""
        # test data below
        self._event_name = u"ObjectCreated:Put"
        self._event_time = u"2016-07-28T16:14:27.809576Z"
        self._bucket_name = u"jen-elife-production-final"
        if bucket_name:
            self._bucket_name = bucket_name
        self._file_name = u"elife-00353-vor-r1.zip"
        self._file_etag = u"e7f639f63171c097d4761e2d2efe8dc4"
        self._file_size = 1097506

    def get_body(self):
        return self.body

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


class FakeSMTPServer:
    def __init__(self, tmp_dir):
        self.number = 0
        self.tmp_dir = tmp_dir

    def sendmail(self, sender, recipient, message):
        self.process_message(None, sender, recipient, message)

    def process_message(self, peer, mailfrom, rcpttos, data):
        filename = os.path.join(
            self.tmp_dir,
            "%s-%d.eml" % (datetime.now().strftime("%Y%m%d%H%M%S"), self.number),
        )
        with open(filename, "w") as open_file:
            open_file.write(data)
        self.number += 1


class FakeBigQueryClient:
    def __init__(self, result):
        self.result = result

    def query(self, query):
        return FakeBigQueryJob(self.result)


class FakeBigQueryJob:
    def __init__(self, result_return):
        self.result_return = result_return

    def result(self):
        return self.result_return


class FakeBigQueryRowIterator:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        for row in self.rows:
            yield row


class FakeFTPServer:
    def __init__(self, dir=None):
        # original directory
        self.dir = dir
        # current working directory
        self.cwd_dir = dir
        self.host = None
        self.passiveserver = True

    def connect(self, uri):
        self.host = uri

    def set_pasv(self, passive):
        self.passiveserver = passive

    def login(self, username, password):
        pass

    def quit(self):
        pass

    def storlines(self, cmd, fp, callback=None):
        if self.cwd_dir:
            filename = cmd.split(" ")[-1]
            with open(os.path.join(self.cwd_dir, filename), "w") as open_file:
                open_file.write(fp.read())

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        if self.cwd_dir:
            filename = cmd.split(" ")[-1]
            with open(os.path.join(self.cwd_dir, filename), "wb") as open_file:
                open_file.write(fp.read())

    def cwd(self, folder_name):
        if self.cwd_dir:
            if folder_name == "/":
                # reset current working directory to original value
                new_dir = self.dir
            else:
                new_dir = os.path.join(self.dir, folder_name.lstrip("/").rstrip("/"))
            if os.path.exists(new_dir):
                self.cwd_dir = new_dir
            else:
                raise ftplib.error_perm("Directory does not exist")

    def mkd(self, folder_name):
        if self.cwd_dir:
            new_dir = os.path.join(self.cwd_dir, folder_name.lstrip("/"))
            os.mkdir(new_dir)
            self.cwd_dir = new_dir
