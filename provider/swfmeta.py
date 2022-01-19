from datetime import datetime, timezone
from collections import OrderedDict
import boto3

"""
SWFMeta data provider
Functions to provide meta data from SWF so code is not duplicated
"""


def utctimestamp(dt):
    "get a timestamp for utc timezone from a datetime object"
    return dt.replace(tzinfo=timezone.utc).timestamp()


class SWFMeta:
    def __init__(self, settings):
        self.settings = settings

        self.client = None

    def connect(self):
        # Simple connect
        self.client = boto3.client(
            "swf",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.swf_region,
        )

    def get_closed_workflow_execution_count(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        start_oldest_date=None,
        start_latest_date=None,
        close_status=None,
    ):
        """
        Get the count of executions from SWF, limited to 90 days by Amazon,
        for the criteria supplied
        Relies on boto.swf.count_closed_workflow_executions
        Note: Cannot send a workflow_name and close_status at the same time
        """
        if self.client is None:
            self.connect()

        if domain is None:
            domain = self.settings.domain

        kwargs = query_kwargs(
            domain,
            workflow_id,
            workflow_name,
            workflow_version,
            start_oldest_date,
            start_latest_date,
            close_status,
        )

        result = self.client.count_closed_workflow_executions(**kwargs)

        return result.get("count")

    def get_closed_workflow_executionInfos(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        start_oldest_date=None,
        start_latest_date=None,
        close_status=None,
        maximum_page_size=100,
    ):
        """
        Get the full history of executions from SWF, limited to 90 days by Amazon,
        for the criteria supplied
        Relies on boto.swf.list_closed_workflow_executions with some wrappers and
        handling of the nextPageToken if encountered
        """
        if self.client is None:
            self.connect()

        if domain is None:
            domain = self.settings.domain

        # Cannot send a workflow_name and close_status at the same time to handle it
        #   {u'message': u'Cannot specify more than one exclusive filters in the
        #    same query: [WorkflowTypeFilter, CloseStatusFilter]
        #   ', u'__type': u'com.amazon.coral.validate#ValidationException'}

        kwargs = query_kwargs(
            domain,
            workflow_id,
            workflow_name,
            workflow_version,
            start_oldest_date,
            start_latest_date,
            close_status,
            maximum_page_size,
        )

        infos = self.client.list_closed_workflow_executions(**kwargs)

        # Still need to handle the nextPageToken
        # Check if there is no nextPageToken, if there is none
        #  return the result, nothing to page
        next_page_token = infos.get("nextPageToken")

        # Continue, we have a nextPageToken. Assemble a full array of events by continually polling
        if next_page_token is not None:
            all_infos = infos["executionInfos"]
            while next_page_token is not None:
                kwargs["nextPageToken"] = next_page_token

                infos = self.client.list_closed_workflow_executions(**kwargs)

                for execution_info in infos.get("executionInfos"):
                    all_infos.append(execution_info)

                next_page_token = infos.get("nextPageToken")

            # Finally, reset the original decision response with the full set of events
            infos["executionInfos"] = all_infos

        # Handle if a close_status was supplied as well as a workflow_name
        if workflow_name is not None and close_status is not None:
            good_infos = []
            for execution in infos["executionInfos"]:
                if execution.get("closeStatus") == close_status:
                    good_infos.append(execution)
            infos["executionInfos"] = good_infos

        return infos

    def get_last_completed_workflow_execution_startTimestamp(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
    ):
        """
        For the specified workflow_id, or workflow_name + workflow_version,
        get the startTimestamp for the last successfully completed workflow
        execution
        Use up to the full 90 days of execution history provided by Amazon, but
        first shorter periods of time as specified in days_list
        """

        latest_start_timestamp = None

        start_latest_date = datetime.utcnow()

        # Number of days to check in successive calls to SWF history
        days_list = [0.25, 1, 7, 90]

        for days in days_list:

            start_oldest_date = datetime.utcfromtimestamp(
                utctimestamp(start_latest_date) - int(60 * 60 * 24 * days)
            )

            close_status = "COMPLETED"

            infos = self.get_closed_workflow_executionInfos(
                domain=domain,
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                workflow_version=workflow_version,
                start_latest_date=start_latest_date,
                start_oldest_date=start_oldest_date,
                close_status=close_status,
            )

            # Find the latest run
            for execution in infos.get("executionInfos"):
                # convert the returned datetime.datetime object to a numeric timestamp
                execution_timestamp = utctimestamp(execution["startTimestamp"])
                if latest_start_timestamp is None:
                    latest_start_timestamp = execution_timestamp
                    continue
                if execution_timestamp > latest_start_timestamp:
                    latest_start_timestamp = execution_timestamp
            # Check if we found the last date
            if latest_start_timestamp:
                break

        return latest_start_timestamp

    def get_open_workflow_executionInfos(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
        oldest_date=None,
        latest_date=None,
        maximum_page_size=100,
    ):
        """
        Get a list of open running workflow executions from SWF, limited to 90 days by Amazon,
        for the criteria supplied
        Relies on boto.swf.list_open_workflow_executions with some wrappers and
        handling of the nextPageToken if encountered
        """
        if self.client is None:
            self.connect()

        if domain is None:
            domain = self.settings.domain

        # Use now as the start_latest_date if not supplied
        if latest_date is None:
            latest_date = datetime.utcnow()
        # Use full 90 day history if start_oldest_date is not supplied
        if oldest_date is None:
            oldest_date = datetime.utcfromtimestamp(
                utctimestamp(latest_date) - (60 * 60 * 24 * 90)
            )

        close_status = None
        kwargs = query_kwargs(
            domain,
            workflow_id,
            workflow_name,
            workflow_version,
            oldest_date,
            latest_date,
            close_status,
            maximum_page_size,
        )

        # Still need to handle the nextPageToken
        infos = self.client.list_open_workflow_executions(**kwargs)

        # Check if there is no nextPageToken, if there is none
        #  return the result, nothing to page
        next_page_token = infos.get("nextPageToken")

        # Continue, we have a nextPageToken. Assemble a full array of events by continually polling
        if next_page_token is not None:
            all_infos = infos["executionInfos"]
            while next_page_token is not None:
                kwargs["nextPageToken"] = next_page_token

                infos = self.client.list_open_workflow_executions(**kwargs)

                for execution_info in infos.get("executionInfos"):
                    all_infos.append(execution_info)

                next_page_token = infos.get("nextPageToken")

            # Finally, reset the original decision response with the full set of events
            infos["executionInfos"] = all_infos

        return infos

    def is_workflow_open(
        self,
        domain=None,
        workflow_id=None,
        workflow_name=None,
        workflow_version=None,
    ):
        """
        For the specified workflow_id, or workflow_name + workflow_version,
        check if the workflow is currently open, in order to check for workflow conflicts
        Use the full 90 days of execution history provided by Amazon
        """

        is_open = None

        # use datetime() values for these
        latest_date = datetime.utcnow()
        oldest_date = datetime.utcfromtimestamp(
            utctimestamp(latest_date) - (60 * 60 * 24 * 90)
        )

        infos = self.get_open_workflow_executionInfos(
            domain=domain,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            latest_date=latest_date,
            oldest_date=oldest_date,
        )

        if len(infos["executionInfos"]) <= 0:
            is_open = False
        else:
            # If there are any list items, then they should be OPEN status
            #  so no need to explore further
            is_open = True

        return is_open


def query_kwargs(
    domain=None,
    workflow_id=None,
    workflow_name=None,
    workflow_version=None,
    start_oldest_date=None,
    start_latest_date=None,
    close_status=None,
    maximum_page_size=None,
):
    "arguments to use in queries of SWF metadata"
    kwargs = OrderedDict()
    kwargs["domain"] = domain
    if start_oldest_date or start_latest_date:
        kwargs["startTimeFilter"] = {}
        if start_oldest_date:
            kwargs["startTimeFilter"]["oldestDate"] = start_oldest_date
        if start_latest_date:
            kwargs["startTimeFilter"]["latestDate"] = start_latest_date
    if workflow_id:
        kwargs["executionFilter"] = {"workflowId": workflow_id}
    if workflow_name or workflow_version:
        kwargs["typeFilter"] = {}
        if workflow_name:
            kwargs["typeFilter"]["name"] = workflow_name
        if workflow_version:
            kwargs["typeFilter"]["version"] = workflow_version
    if close_status is not None and (workflow_name is None and workflow_id is None):
        kwargs["closeStatusFilter"] = {"status": close_status}
    if maximum_page_size:
        kwargs["maximumPageSize"] = maximum_page_size
    return kwargs
