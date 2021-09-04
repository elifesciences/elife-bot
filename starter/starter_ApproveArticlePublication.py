import json
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params

"""
Amazon SWF PublishArticle starter, for API and Lens publishing etc.
"""


class starter_ApproveArticlePublication(Starter):
    def get_workflow_params(
        self,
        article_id=None,
        version=None,
        run=None,
        publication_data=None,
        workflow=None,
    ):
        if workflow is None:
            raise NullRequiredDataException("Did not get a workflow parameter")

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (workflow, article_id)
        workflow_params["workflow_name"] = workflow
        workflow_params["workflow_version"] = "1"

        if article_id is None or version is None or publication_data is None:
            raise NullRequiredDataException(
                "Did not get an article id, version or publication data"
            )

        info = {
            "article_id": article_id,
            "version": str(version),
            "run": run,
            "publication_data": publication_data,
        }
        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(
        self,
        settings,
        article_id=None,
        version=None,
        run=None,
        publication_data=None,
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(
            article_id,
            version,
            run,
            publication_data,
            workflow="ApproveArticlePublication",
        )

    def start_workflow(
        self,
        article_id=None,
        version=None,
        run=None,
        publication_data=None,
        workflow="ApproveArticlePublication",
    ):

        workflow_params = self.get_workflow_params(
            article_id, version, run, publication_data, workflow
        )

        self.connect_to_swf()

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
