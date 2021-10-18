from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF PublishPOA starter
"""


class starter_PublishPOA(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_PublishPOA, self).__init__(settings, logger, "PublishPOA")

    def get_workflow_params(self):
        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = self.name
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 35)
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

    STARTER = starter_PublishPOA(SETTINGS)

    STARTER.start_workflow()
