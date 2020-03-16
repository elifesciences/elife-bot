from starter.objects import Starter, get_workflow_params
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
            workflow_params = get_workflow_params(workflow)

            # add domain and task list
            workflow_params['domain'] = self.settings.domain
            workflow_params['task_list'] = self.settings.default_task_list

            # start a workflow execution
            self.logger.info('Starting workflow: %s', workflow_params.get('workflow_id'))
            try:
                self.start_swf_workflow_execution(workflow_params)
            except:
                message = (
                    'Exception starting workflow execution for workflow_id %s' %
                    workflow_params.get('workflow_id'))
                self.logger.exception(message)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER_OBJECT = starter_Ping(SETTINGS)

    STARTER_OBJECT.start_workflow()
