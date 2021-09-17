import json
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params

"""
Amazon SWF PublishArticle starter, for API and Lens publishing etc.
"""


class starter_ApproveArticlePublication(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_ApproveArticlePublication, self).__init__(
            settings, logger, "ApproveArticlePublication"
        )

    def get_workflow_params(
        self, article_id=None, version=None, run=None, publication_data=None
    ):
        if article_id is None or version is None or publication_data is None:
            raise NullRequiredDataException(
                "Did not get an article id, version or publication data"
            )

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (self.name, article_id)
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"

        info = {
            "article_id": article_id,
            "version": str(version),
            "run": run,
            "publication_data": publication_data,
        }
        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(
        self, settings, article_id=None, version=None, run=None, publication_data=None
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(article_id, version, run, publication_data)

    def start_workflow(
        self, article_id=None, version=None, run=None, publication_data=None
    ):

        workflow_params = self.get_workflow_params(
            article_id, version, run, publication_data
        )

        self.start_workflow_execution(workflow_params)
