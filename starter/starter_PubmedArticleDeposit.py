import boto.swf
import log
import json
import random
from provider import utils

"""
Amazon SWF PubmedArticleDeposit starter
"""


class starter_PubmedArticleDeposit():

    def start(self, settings):
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        logger = log.logger(logFile, settings.setLevel, identity)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        # Start a workflow execution
        workflow_id = "PubmedArticleDeposit"
        workflow_name = "PubmedArticleDeposit"
        workflow_version = "1"
        child_policy = None
        execution_start_to_close_timeout = None
        input = None

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name,
                                                     workflow_version, settings.default_task_list,
                                                     child_policy,
                                                     execution_start_to_close_timeout,
                                                     input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                       'a running workflow with ID %s' % workflow_id)
            print(message)
            logger.info(message)

if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    o = starter_PubmedArticleDeposit()

    o.start(settings=SETTINGS)
