import random
import json
from collections import OrderedDict
import boto3
import botocore
import starter.starter_helper as helper


LOG_FILE = "starter.log"


class Starter:

    # Base class
    def __init__(self, settings=None, logger=None, name=None):
        self.settings = settings
        self.name = name
        self.logger = logger
        self.client = None

        # logging
        if not self.logger:
            self.instantiate_logger()

    def instantiate_logger(self):
        if not self.logger and self.settings:
            if self.name:
                identity = helper.get_starter_identity(self.name)
            else:
                identity = "starter_%s" % int(random.random() * 1000)

            self.logger = helper.get_starter_logger(
                self.settings.setLevel, identity, log_file=LOG_FILE
            )

    def connect_to_swf(self):
        "connect to SWF"
        self.client = boto3.client(
            "swf",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.swf_region,
        )

    def start_workflow_execution(self, workflow_params):
        "start a workflow execution with exception handling and logging messages"

        self.connect_to_swf()

        self.logger.info("Starting workflow: %s", workflow_params.get("workflow_id"))
        try:
            self.start_swf_workflow_execution(workflow_params)
        except:
            message = (
                "Exception starting workflow execution for workflow_id %s"
                % workflow_params.get("workflow_id")
            )
            self.logger.exception(message)

    def start_swf_workflow_execution(self, workflow_params):
        if not self.client:
            self.connect_to_swf()

        kwargs = {
            "domain": workflow_params.get("domain"),
            "workflowId": workflow_params.get("workflow_id"),
            "workflowType": {
                "name": workflow_params.get("workflow_name"),
                "version": workflow_params.get("workflow_version"),
            },
        }
        if workflow_params.get("task_list"):
            kwargs["taskList"] = {"name": workflow_params.get("task_list")}
        if workflow_params.get("child_policy"):
            kwargs["childPolicy"] = workflow_params.get("child_policy")
        if workflow_params.get("execution_start_to_close_timeout"):
            kwargs["executionStartToCloseTimeout"] = workflow_params.get(
                "execution_start_to_close_timeout"
            )
        if workflow_params.get("input"):
            kwargs["input"] = workflow_params.get("input")

        try:
            response = self.client.start_workflow_execution(**kwargs)
            self.logger.info(
                "got response: \n%s", json.dumps(response, sort_keys=True, indent=4)
            )

        except botocore.exceptions.ClientError as exception:
            # There is already a running workflow with that ID, cannot start another
            if (
                exception.response["Error"]["Code"]
                == "WorkflowExecutionAlreadyStartedFault"
            ):
                message = (
                    "WorkflowExecutionAlreadyStartedFault: There is already "
                    + "a running workflow with ID %s"
                    % workflow_params.get("workflow_id")
                )
            else:
                message = (
                    "Unhandled botocore.exceptions.ClientError exception "
                    + "for workflow with ID %s" % workflow_params.get("workflow_id")
                )
            print(message)
            self.logger.info(message)
            raise


def default_workflow_params(settings):

    workflow_params = OrderedDict()
    workflow_params["domain"] = settings.domain
    workflow_params["task_list"] = settings.default_task_list
    workflow_params["workflow_id"] = None
    workflow_params["workflow_name"] = None
    workflow_params["workflow_version"] = None
    workflow_params["child_policy"] = None
    workflow_params["execution_start_to_close_timeout"] = None
    workflow_params["input"] = None

    return workflow_params
