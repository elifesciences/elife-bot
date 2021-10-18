import random
from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF Ping workflow starter
"""


class starter_Ping(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_Ping, self).__init__(settings, logger, "Ping")

    def get_workflow_params(self):
        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            int(random.random() * 10000),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        return workflow_params

    def start(self, settings):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow()

    def start_workflow(self):

        workflow_params = self.get_workflow_params()
        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_Ping(SETTINGS)

    STARTER.start_workflow()
