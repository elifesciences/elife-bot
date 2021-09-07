from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF Admin Email starter
"""


class starter_AdminEmail(Starter):
    def get_workflow_params(self):
        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "AdminEmail"
        workflow_params["workflow_name"] = "AdminEmail"
        workflow_params["workflow_version"] = "1"
        return workflow_params

    def start(self, settings):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow()

    def start_workflow(self):

        self.connect_to_swf()

        workflow_params = self.get_workflow_params()

        # start a workflow execution
        self.logger.info("Starting workflow: %s", workflow_params.get("workflow_id"))
        try:
            self.start_swf_workflow_execution(workflow_params)
        except:
            message = (
                "Exception starting workflow execution for workflow_id %s"
                % workflow_params.get("workflow_id")
            )
            self.logger.exception(message)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_AdminEmail(SETTINGS)

    STARTER.start_workflow()
