import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import settings as settingsLib
import log
import json
import random
from optparse import OptionParser

"""
Amazon SWF PubRouterDeposit starter
"""

class starter_PubRouterDeposit():

    def start(self, ENV="dev", workflow=None):
        # Specify run environment settings
        settings = settingsLib.get_settings(ENV)

        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        if workflow is not None:
            (workflow_id, workflow_name, workflow_version, \
                child_policy, execution_start_to_close_timeout, \
                input) = self.get_workflow_params(workflow, settings)

            # Start a workflow execution
            try:
                response = conn.start_workflow_execution(settings.domain, workflow_id, \
                                        workflow_name, workflow_version, \
                                        settings.default_task_list, child_policy, \
                                        execution_start_to_close_timeout, input)

                logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

            except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                # There is already a running workflow with that ID, cannot start another
                message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                           'a running workflow with ID %s' % workflow_id)
                print message
                logger.info(message)

    def get_workflow_params(self, workflow, settings):

        workflow_id = None
        workflow_name = None
        workflow_version = None
        child_policy = None
        execution_start_to_close_timeout = None

        execution_start_to_close_timeout = None
        input = None

        if (workflow == 'HEFCE'
                or workflow == 'Cengage'
                or workflow == 'GoOA'):
            workflow_id = "PubRouterDeposit_" + workflow

        # workflow_id as set above
        workflow_id = workflow_id
        workflow_name = "PubRouterDeposit"
        workflow_version = "1"

        data = {}
        data['workflow'] = workflow

        input_json = {}
        input_json['data'] = data

        input = json.dumps(input_json)

        return (workflow_id, workflow_name, workflow_version, child_policy, \
                execution_start_to_close_timeout, input)

if __name__ == "__main__":

    workflow = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string",
                      dest="env", help="set the environment to run, either dev or live")
    parser.add_option("-w", "--workflow-name", default=None, action="store", type="string",
                      dest="workflow", help="specify the workflow name to start")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.workflow:
        workflow = options.workflow

    o = starter_PubRouterDeposit()

    o.start(ENV, workflow=workflow)
