import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import json
import random
from provider import utils

"""
Amazon SWF Ping workflow starter
"""

class starter_Ping():

    def start(self, settings, workflow="Ping"):
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
        if workflow:
            (workflow_id, workflow_name, workflow_version, child_policy,
             execution_start_to_close_timeout, input) = self.get_workflow_params(workflow)

            logger.info('Starting workflow: %s' % workflow_id)
            try:
                response = conn.start_workflow_execution(settings.domain, workflow_id,
                                                         workflow_name, workflow_version,
                                                         settings.default_task_list, child_policy,
                                                         execution_start_to_close_timeout, input)

                logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

            except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                # There is already a running workflow with that ID, cannot start another
                message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                           'a running workflow with ID %s' % workflow_id)
                print(message)
                logger.info(message)

    def get_workflow_params(self, workflow):

        workflow_id = None
        workflow_name = None
        workflow_version = None
        child_policy = None
        execution_start_to_close_timeout = None

        input = None

        if workflow == "Ping":
            workflow_id = "ping_%s" % int(random.random() * 10000)
            workflow_name = "Ping"
            workflow_version = "1"
            child_policy = None
            execution_start_to_close_timeout = None
            input = None

        return (workflow_id, workflow_name, workflow_version, child_policy,
                execution_start_to_close_timeout, input)

if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    o = starter_Ping()

    o.start(settings=SETTINGS)
