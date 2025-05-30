import json
import uuid
from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF FindNewDocmaps starter
"""


class starter_FindNewDocmaps(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_FindNewDocmaps, self).__init__(
            settings, logger, "FindNewDocmaps"
        )

    def get_workflow_params(self, run=None):
        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = self.name
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        info = {"run": run}
        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(self, settings, run=None):
        "method for backwards compatibility"
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow()

    def start_workflow(self, run=None):
        if run is None:
            run = str(uuid.uuid4())
        workflow_params = self.get_workflow_params(run)
        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_FindNewDocmaps(SETTINGS)

    STARTER.start_workflow()
