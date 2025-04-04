import json
import time
from provider import utils


"""
Amazon SWF workflow base class
"""


class WorkflowLayer1Decisions:
    "replaces boto2 Layer1Decisions functionality"

    def __init__(self):
        self.data = []

    def fail_workflow_execution(self, reason=None):
        self.data.append(
            {
                "decisionType": "FailWorkflowExecution",
                "failWorkflowExecutionDecisionAttributes": {},
            }
        )
        if reason:
            self.data.append(
                {
                    "decisionType": "FailWorkflowExecution",
                    "failWorkflowExecutionDecisionAttributes": {
                        "reason": "%s" % reason
                    },
                }
            )

    def schedule_activity_task(self, **kwargs):
        """example decision
        {
            "decisionType": "ScheduleActivityTask",
            "scheduleActivityTaskDecisionAttributes": {
                "activityId": "PingWorker",
                "activityType": {"name": "PingWorker", "version": "1"},
                "taskList": {"name": "DefaultTaskList"},
                "control": "control data",
                "heartbeatTimeout": "300",
                "scheduleToCloseTimeout": "300",
                "scheduleToStartTimeout": "300",
                "startToCloseTimeout": "300",
                "input": "null",
            },
        }
        """
        decision = {}
        decision["decisionType"] = "ScheduleActivityTask"

        attributes = {}
        attributes["activityId"] = str(kwargs.get("activity_id"))
        attributes["activityType"] = {
            "name": str(kwargs.get("activity_type_name")),
            "version": str(kwargs.get("activity_type_version")),
        }
        if kwargs.get("task_list"):
            attributes["taskList"] = {"name": str(kwargs.get("task_list"))}

        if kwargs.get("control"):
            attributes["control"] = str(kwargs.get("control_data"))
        if kwargs.get("heartbeat_timeout"):
            attributes["heartbeatTimeout"] = str(kwargs.get("heartbeat_timeout"))
        if kwargs.get("schedule_to_close_timeout"):
            attributes["scheduleToCloseTimeout"] = str(
                kwargs.get("schedule_to_close_timeout")
            )
        if kwargs.get("schedule_to_start_timeout"):
            attributes["scheduleToStartTimeout"] = str(
                kwargs.get("schedule_to_start_timeout")
            )
        if kwargs.get("start_to_close_timeout"):
            attributes["startToCloseTimeout"] = str(
                kwargs.get("start_to_close_timeout")
            )
        if kwargs.get("input"):
            attributes["input"] = str(kwargs.get("input"))
        decision["scheduleActivityTaskDecisionAttributes"] = attributes
        self.data.append(decision)

    def complete_workflow_execution(self):
        self.data.append(
            {
                "decisionType": "CompleteWorkflowExecution",
                "completeWorkflowExecutionDecisionAttributes": {},
            }
        )


class Workflow(object):
    # Base class for extending
    def __init__(
        self,
        settings,
        logger,
        client=None,
        token=None,
        decision=None,
        maximum_page_size=100,
        definition=None,
    ):
        self.settings = settings
        self.logger = logger
        self.token = token
        self.decision = decision
        self.maximum_page_size = maximum_page_size
        self.definition = None
        if definition is not None:
            self.load_definition(definition)
        # boto3 swf client
        self.client = client

        # SWF Defaults, most are set in derived classes or at runtime
        try:
            self.domain = self.settings.domain
        except AttributeError:
            self.domain = None

        try:
            self.task_list = self.settings.default_task_list
        except AttributeError:
            self.task_list = None

        self.name = None
        self.version = None
        self.default_child_policy = "TERMINATE"
        self.default_execution_start_to_close_timeout = 60 * 10
        self.default_task_start_to_close_timeout = 30
        self.description = None

    def load_definition(self, definition):
        """
        Given a JSON representation of an entire workflow definition,
        as specified for processing a workflow, parse and load the data
        """
        self.definition = definition

    def get_definition(self):
        """
        Return a JSON represetation of the workflow definition,
        if present
        """
        if self.definition is None:
            return None
        return self.definition

    def complete_workflow(self):
        """
        Signal the workflow is completed to SWF
        """
        workflow_decisions = WorkflowLayer1Decisions()
        workflow_decisions.complete_workflow_execution()
        self.complete_decision(workflow_decisions)
        # out = self.conn.respond_decision_task_completed(
        #    taskToken=self.token, decisions=workflow_decisions.data
        # )
        # self.logger.info("respond_decision_task_completed returned %s" % out)

    def complete_decision(self, workflow_decisions=None):
        """
        Signal a decision was made to SWF
        """
        out = self.client.respond_decision_task_completed(
            taskToken=self.token, decisions=workflow_decisions.data
        )
        self.logger.info("respond_decision_task_completed returned %s" % out)

    def is_workflow_complete(self):
        """
        Check each step was completed to determine if workflow is complete
        """
        for step in self.definition["steps"]:
            # Check for single or multiple activities in the step
            if type(step) == list:
                # Is a list of activities to complete in parallel
                for p_activity in step:
                    activityType = p_activity["activity_type"]
                    activityID = p_activity["activity_id"]
                    if (
                        self.activity_status(self.decision, activityType, activityID)
                        is False
                    ):
                        return False
            else:
                # A single activity
                activityType = step["activity_type"]
                activityID = step["activity_id"]

                if (
                    self.activity_status(self.decision, activityType, activityID)
                    is False
                ):
                    return False

        return True

    def get_next_activities(self):
        """
        For each step of a workflow, determine which activities are completed
        and return the activities to start next
        """
        activities = []

        for step in self.definition["steps"]:
            # Check for single or multiple activities in the step
            if type(step) == list:
                # Is a list of activities to complete in parallel
                # Check if the entire list of activities is completed
                all_completed = True
                none_started = True
                for p_activity in step:
                    activityType = p_activity["activity_type"]
                    activityID = p_activity["activity_id"]
                    if (
                        self.activity_status(self.decision, activityType, activityID)
                        is False
                    ):
                        all_completed = False
                    if (
                        self.activity_status(self.decision, activityType, activityID)
                        is True
                    ):
                        none_started = False
                if all_completed == False and none_started is True:
                    # A fresh step not started yet, add the activities
                    for p_activity in step:
                        activities.append(p_activity)

            else:
                # A single activity
                activityType = step["activity_type"]
                activityID = step["activity_id"]

                if (
                    self.activity_status(self.decision, activityType, activityID)
                    is False
                ):
                    # Only add one activity at a time, for now
                    # if(len(activities) == 0):
                    activities.append(step)

            # Return the activities not completed yet
            if len(activities) > 0:
                return activities

        return activities

    def schedule_activity(self, activity, workflow_decisions=None):
        """
        Given a JSON representation for an activity,
        format a ScheduleActivityTask decision
        message and return it
        """

        # Cast all values to string
        task_list = str(self.definition["task_list"])

        activity_id = str(activity["activity_id"])
        # activity_id = activity_id + '.' + self.get_time() + '.%s' % int(random.random() * 10000)
        activity_type = str(activity["activity_type"])
        version = str(activity["version"])
        heartbeat_timeout = str(activity["heartbeat_timeout"])
        schedule_to_close_timeout = str(activity["schedule_to_close_timeout"])
        schedule_to_start_timeout = str(activity["schedule_to_start_timeout"])
        start_to_close_timeout = str(activity["start_to_close_timeout"])
        data = json.dumps(activity["input"])

        self.logger.info("scheduling task: %s" % activity_id)
        if workflow_decisions is None:
            workflow_decisions = WorkflowLayer1Decisions()
        workflow_decisions.schedule_activity_task(
            activity_id=activity_id,  # Activity ID
            activity_type_name=activity_type,  # Activity Type
            activity_type_version=version,  # Activity Type Version
            task_list=task_list,  # Task List
            control="control data",  # control
            heartbeat_timeout=heartbeat_timeout,  # Heartbeat in seconds
            schedule_to_close_timeout=schedule_to_close_timeout,  # schedule_to_close_timeout
            schedule_to_start_timeout=schedule_to_start_timeout,  # schedule_to_start_timeout
            start_to_close_timeout=start_to_close_timeout,  # start_to_close_timeout
            input=data,  # input: extra data to pass to activity
        )

        return workflow_decisions

    def get_time(self):
        """
        Return the current time in UTC for logging
        """
        return utils.get_current_datetime().strftime("%Y-%m-%dT%H:%M:%SZ")

    def activity_status(self, decision, activityType=None, activityID=None):
        """
        Given an activityType and/or activityID as the activity details, and
        a decision response from SWF, determine whether the
        activity was successfully run
        """

        if activityType is None and activityID is None:
            return False

        eventId_list = []

        for event in decision["events"]:
            eventId = None
            # Find the all matching eventID for the activityType and/or activityID
            if activityType is not None and activityID is not None:
                try:
                    if (
                        event["activityTaskScheduledEventAttributes"]["activityType"][
                            "name"
                        ]
                        == activityType
                        and event["activityTaskScheduledEventAttributes"]["activityId"]
                        == activityID
                    ):
                        eventId_list.append(event["eventId"])
                except KeyError:
                    pass
            elif activityType is not None and activityID is None:
                try:
                    if (
                        event["activityTaskScheduledEventAttributes"]["activityType"][
                            "name"
                        ]
                        == activityType
                    ):
                        eventId_list.append(event["eventId"])
                except KeyError:
                    pass
            elif activityID is not None and activityType is None:
                try:
                    if (
                        event["activityTaskScheduledEventAttributes"]["activityId"]
                        == activityID
                    ):
                        eventId_list.append(event["eventId"])
                except KeyError:
                    pass

        # Now if we have an eventId, find if in the decision history is was
        #  successfully completed
        if len(eventId_list) <= 0:
            return False
        for event in decision["events"]:
            for eventId in eventId_list:
                # Find the first matching eventID for the activityType
                try:
                    if (
                        event["activityTaskCompletedEventAttributes"][
                            "scheduledEventId"
                        ]
                        == eventId
                    ):
                        # Found matching data, now check completion
                        if event["eventType"] == "ActivityTaskCompleted":
                            # Good!
                            return True
                        break
                except KeyError:
                    pass
        # Default
        return False

    def last_activity_status(self, decision):
        """
        Given a decision response from SWF, determine whether the
        last run activity Failed or Completed
        """
        status = None
        # Traverse the array in reverse order
        for event in decision["events"][::-1]:
            if event["eventType"] == "ActivityTaskCompleted":
                status = "ActivityTaskCompleted"
                break
            elif event["eventType"] == "ActivityTaskFailed":
                status = "ActivityTaskFailed"
                break

        return status

    def handle_nextPageToken(self):
        # Quick test for nextPageToken
        try:
            if self.decision["nextPageToken"]:
                # nextPageToken should be paging if the decider is configured properly
                #  If there is a nextPageToken
                #  something has gone wrong and terminate the workflow execution with
                #  extreme prejudice
                workflow_decisions = WorkflowLayer1Decisions()
                reason = (
                    "nextPageToken found, maximum_page_size of "
                    + str(self.maximum_page_size)
                    + " exceeded"
                )
                workflow_decisions.fail_workflow_execution(reason)
                out = self.client.respond_decision_task_completed(
                    taskToken=self.token, decisions=workflow_decisions.data
                )
                self.logger.info(reason)
                self.logger.info("respond_decision_task_completed returned %s" % out)
                self.token = None
                return False
        except KeyError:
            # No nextPageToken, so we did not exceed the maximum_page_size, continue
            pass

    def get_input(self):
        """
        From the decision response, which is JSON data form SWF, get the
        input data that started the workflow
        """
        if self.decision is None:
            return None
        try:
            input = json.loads(
                self.decision["events"][0]["workflowExecutionStartedEventAttributes"][
                    "input"
                ]
            )
        except KeyError:
            input = None
        return input

    def check_for_failed_workflow_request(self, decision):
        try:
            # Traverse the array in reverse order
            # This is an optimisation since if there is a failure record it will
            # always be at the end of the array
            for event in decision["events"][::-1]:
                if event["eventType"] == "WorkflowExecutionCancelRequested":
                    # terminate
                    workflow_decisions = WorkflowLayer1Decisions()
                    workflow_decisions.fail_workflow_execution()
                    self.complete_decision(workflow_decisions)
                    return
        except TypeError:
            pass

    def rate_limit_failed_activity(self, decision):
        """
        To slow down workflows with missing activity types,
        if the previous activity failed, wait for a bit
        """
        try:
            if self.last_activity_status(decision) == "ActivityTaskFailed":
                time.sleep(10)
        except TypeError:
            pass

    def do_workflow(self, data=None):
        """
        Make decisions and process the workflow accordingly
        """

        # Quick test for nextPageToken
        self.handle_nextPageToken()

        # Schedule an activity
        if self.token is not None:
            # 1. Check if the workflow is completed
            if self.is_workflow_complete():
                # Complete the workflow execution
                self.complete_workflow()
            else:
                # check if the failed activity signalled a request to fail the workflow
                self.check_for_failed_workflow_request(self.decision)
                self.rate_limit_failed_activity(self.decision)
                # 2. Get the next activity
                next_activities = self.get_next_activities()
                workflow_decisions = None
                for activity in next_activities:
                    # Schedule each activity
                    workflow_decisions = self.schedule_activity(
                        activity, workflow_decisions
                    )
                self.complete_decision(workflow_decisions)

        return True

    def describe(self):
        """
        Describe workflow type from SWF, to confirm it exists
        Requires object to have an SWF client using boto3
        """
        if (
            self.client is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        workflow_type = {"name": self.name, "version": self.version}

        try:
            response = self.client.describe_workflow_type(
                domain=self.domain, workflowType=workflow_type
            )
        except self.client.exceptions.UnknownResourceFault:
            response = None

        return response

    def register(self):
        """
        Register the workflow type with SWF, if it does not already exist
        Requires object to have an SWF client using boto3
        """
        if (
            self.client is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        if self.describe() is None:
            response = self.client.register_workflow_type(
                domain=str(self.domain),
                name=str(self.name),
                version=str(self.version),
                description=str(self.description),
                defaultTaskStartToCloseTimeout=str(
                    self.default_task_start_to_close_timeout
                ),
                defaultExecutionStartToCloseTimeout=str(
                    self.default_execution_start_to_close_timeout
                ),
                defaultTaskList={"name": str(self.task_list)},
                defaultChildPolicy=str(self.default_child_policy),
            )
            return response
