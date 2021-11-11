import json
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF PublishArticle starter, for Fluidinfo API publishing
"""

WORKFLOW_NAMES = [
    "HEFCE",
    "Cengage",
    "WoS",
    "GoOA",
    "CNPIEC",
    "CNKI",
    "CLOCKSS",
    "OVID",
    "Zendy",
    "OASwitchboard",
]


class starter_FTPArticle(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_FTPArticle, self).__init__(settings, logger, "FTPArticle")

    def get_workflow_params(self, workflow=None, doi_id=None):
        if workflow is None:
            raise NullRequiredDataException(
                "Did not get a workflow argument. Required."
            )
        if workflow not in WORKFLOW_NAMES:
            raise NullRequiredDataException(
                "Value of workflow not found in supported WORKFLOW_NAMES."
            )
        if doi_id is None:
            raise NullRequiredDataException("Did not get a doi_id argument. Required.")

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s_%s" % (self.name, workflow, doi_id)
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 60 * 23)

        data = {}
        data["workflow"] = workflow
        data["elife_id"] = doi_id

        info = {
            "data": data,
        }

        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(self, settings, workflow=None, doi_id=None):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(
            workflow,
            doi_id,
        )

    def start_workflow(self, workflow=None, doi_id=None):

        workflow_params = self.get_workflow_params(workflow, doi_id)

        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":

    ENV, DOI_ID, WORKFLOW = utils.console_start_env_workflow_doi_id()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_FTPArticle(SETTINGS)

    STARTER.start_workflow(workflow=WORKFLOW, doi_id=DOI_ID)
