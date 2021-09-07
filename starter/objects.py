import random
import json
from collections import OrderedDict
import boto.swf
import starter.starter_helper as helper


LOG_FILE = "starter.log"


class Starter:

    # Base class
    def __init__(self, settings=None, logger=None, name=None):
        self.settings = settings
        self.name = name
        self.logger = logger
        self.conn = None

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
        """connect to SWF"""
        # Simple connect
        self.conn = boto.swf.layer1.Layer1(
            self.settings.aws_access_key_id, self.settings.aws_secret_access_key
        )

    def start_swf_workflow_execution(self, workflow_params):
        if not self.conn:
            self.connect_to_swf()

        try:
            response = self.conn.start_workflow_execution(
                workflow_params.get("domain"),
                workflow_params.get("workflow_id"),
                workflow_params.get("workflow_name"),
                workflow_params.get("workflow_version"),
                task_list=workflow_params.get("task_list"),
                child_policy=workflow_params.get("child_policy"),
                execution_start_to_close_timeout=workflow_params.get(
                    "execution_start_to_close_timeout"
                ),
                input=workflow_params.get("input"),
            )

            self.logger.info(
                "got response: \n%s", json.dumps(response, sort_keys=True, indent=4)
            )

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = (
                "SWFWorkflowExecutionAlreadyStartedError: There is already "
                + "a running workflow with ID %s" % workflow_params.get("workflow_id")
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
