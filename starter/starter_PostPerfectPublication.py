import json
from starter.objects import Starter, default_workflow_params
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF PostPerfectPublication starter, for API and Lens publishing etc.
"""


class starter_PostPerfectPublication(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_PostPerfectPublication, self).__init__(
            settings, logger, "PostPerfectPublication"
        )

    def get_workflow_params(self, info):
        workflow_params = default_workflow_params(self.settings)

        if info.get("article_id") is None:
            raise NullRequiredDataException(
                "article id is Null. Possible error: "
                "Lax did not send back valid data from ingest."
            )

        publication_from = "lax" if "requested_action" in info else "website"

        workflow_params["workflow_id"] = "%s_%s.%s.%s" % (
            self.name,
            info.get("article_id"),
            info.get("version"),
            publication_from,
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"

        workflow_params["input"] = json.dumps(info, default=lambda ob: None)

        return workflow_params

    def start(self, info, settings):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(info)

    def start_workflow(self, info):

        workflow_params = self.get_workflow_params(info)

        self.connect_to_swf()

        # start a workflow execution
        self.logger.info("Starting workflow: %s", workflow_params.get("workflow_id"))
        try:
            self.start_swf_workflow_execution(workflow_params)
        except NullRequiredDataException as null_exception:
            self.logger.exception(null_exception.message)
            raise
        except:
            message = (
                "Exception starting workflow execution for workflow_id %s"
                % workflow_params.get("workflow_id")
            )
            self.logger.exception(message)
