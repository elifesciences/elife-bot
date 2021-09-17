import json
from provider import utils
from starter.objects import Starter, default_workflow_params
from starter.starter_helper import NullRequiredDataException


"""
Amazon SWF LensArticlePublish starter
"""


class starter_LensArticlePublish(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_LensArticlePublish, self).__init__(
            settings, logger, "LensArticlePublish"
        )

    def get_workflow_params(self, doi_id=None):

        if not doi_id:
            raise NullRequiredDataException(
                "Did not get doi_id in starter %s" % self.name
            )

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            doi_id,
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 30)

        input_data = {}
        if doi_id:
            input_data["article_id"] = utils.pad_msid(doi_id)
        workflow_params["input"] = json.dumps(input_data, default=lambda ob: None)

        return workflow_params

    def start(self, settings, doi_id):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(doi_id)

    def start_workflow(self, doi_id=None):

        workflow_params = self.get_workflow_params(doi_id)
        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":

    ENV, DOI_ID = utils.console_start_env_doi_id()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_LensArticlePublish()

    STARTER.start(settings=SETTINGS, doi_id=DOI_ID)
