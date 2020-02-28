import json
import random
import boto.swf
from starter.objects import Starter
from provider import utils

"""
Amazon SWF Ping workflow starter
"""


class starter_Ping(Starter):

    def start(self, workflow="Ping"):

        self.connect_to_swf()

        if workflow:
            (workflow_id, workflow_name, workflow_version, child_policy,
             execution_start_to_close_timeout, workflow_input) = self.get_workflow_params(workflow)

            self.logger.info('Starting workflow: %s', workflow_id)
            try:
                response = self.conn.start_workflow_execution(
                    self.settings.domain, workflow_id,
                    workflow_name, workflow_version,
                    self.settings.default_task_list, child_policy,
                    execution_start_to_close_timeout, workflow_input)

                self.logger.info(
                    'got response: \n%s', json.dumps(response, sort_keys=True, indent=4))

            except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                # There is already a running workflow with that ID, cannot start another
                message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                           'a running workflow with ID %s' % workflow_id)
                print(message)
                self.logger.info(message)

    def get_workflow_params(self, workflow):

        workflow_id = None
        workflow_name = None
        workflow_version = None
        child_policy = None
        execution_start_to_close_timeout = None

        workflow_input = None

        if workflow == "Ping":
            workflow_id = "ping_%s" % int(random.random() * 10000)
            workflow_name = "Ping"
            workflow_version = "1"
            child_policy = None
            execution_start_to_close_timeout = None
            workflow_input = None

        return (workflow_id, workflow_name, workflow_version, child_policy,
                execution_start_to_close_timeout, workflow_input)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER_OBJECT = starter_Ping(SETTINGS)

    STARTER_OBJECT.start()
