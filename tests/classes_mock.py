import time
import os
import ftplib
from datetime import datetime


class FakeSWFClient:
    def __init__(self, *args, **kwargs):
        # infos is JSON format infos in SWF format for workflow executions
        self.infos = []
        self.infos_counter = 0

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

    def poll_for_activity_task(self, domain, task_list, identity=None):
        pass

    def respond_activity_task_failed(self, **kwargs):
        pass

    def respond_activity_task_completed(self, **kwargs):
        pass

    def request_cancel_workflow_execution(self, **kwargs):
        pass

    def start_workflow_execution(self, **kwargs):
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
