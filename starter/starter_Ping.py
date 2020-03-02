import random
from collections import OrderedDict
from starter.objects import Starter
from provider import utils

"""
Amazon SWF Ping workflow starter
"""


class starter_Ping(Starter):

    def start(self, settings, workflow="Ping"):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(workflow)

    def start_workflow(self, workflow="Ping"):

        self.connect_to_swf()

        if workflow:
            (workflow_id, workflow_name, workflow_version, child_policy,
             execution_start_to_close_timeout, workflow_input) = self.get_workflow_params(workflow)

            # temporary workflow_params var
            workflow_params = OrderedDict()
            workflow_params['domain'] = self.settings.domain
            workflow_params['workflow_id'] = workflow_id
            workflow_params['workflow_name'] = workflow_name
            workflow_params['workflow_version'] = workflow_version
            workflow_params['task_list'] = self.settings.default_task_list
            workflow_params['child_policy'] = child_policy
            workflow_params['execution_start_to_close_timeout'] = execution_start_to_close_timeout
            workflow_params['input'] = workflow_input

            self.logger.info('Starting workflow: %s', workflow_id)
            try:
                self.start_swf_workflow_execution(workflow_params)
            except:
                message = (
                    'Exception starting workflow execution for workflow_id %s' %
                    workflow_params.get('workflow_id'))
                self.logger.exception(message)

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

    STARTER_OBJECT.start_workflow()
