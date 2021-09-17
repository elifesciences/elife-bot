import json
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF PubRouterDeposit starter
"""


class starter_PubRouterDeposit(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_PubRouterDeposit, self).__init__(
            settings, logger, "PubRouterDeposit"
        )

    def get_workflow_params(self, workflow=None):
        if workflow is None:
            raise NullRequiredDataException(
                "Did not get a workflow argument. Required."
            )

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (self.name, workflow)
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"

        data = {}
        data["workflow"] = workflow

        info = {
            "data": data,
        }

        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(self, settings, workflow=None):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(workflow)

    def start_workflow(self, workflow=None):

        workflow_params = self.get_workflow_params(workflow)

        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":

    ENV, WORKFLOW = utils.console_start_env_workflow()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_PubRouterDeposit(SETTINGS)

    STARTER.start_workflow(workflow=WORKFLOW)
