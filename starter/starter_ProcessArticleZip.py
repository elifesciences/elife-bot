import json
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params

"""
Amazon SWF ProcessArticleZip starter, preparing article xml for lax.
"""


class starter_ProcessArticleZip(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_ProcessArticleZip, self).__init__(
            settings, logger, "ProcessArticleZip"
        )

    def get_workflow_params(self, info):
        workflow_params = default_workflow_params(self.settings)

        if (
            info.get("article_id") is None
            or info.get("run") is None
            or info.get("version") is None
        ):
            raise NullRequiredDataException(
                "article id or version or run is Null. "
                "Possible error: Lax did not send back valid data from ingest."
            )

        workflow_params["workflow_id"] = "%s_%s.%s" % (
            self.name,
            info.get("article_id"),
            info.get("version"),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"

        workflow_params["input"] = json.dumps(info, default=lambda ob: None)

        return workflow_params

    def start(
        self,
        settings,
        article_id,
        version,
        requested_action,
        force,
        result,
        expanded_folder,
        status,
        run,
        update_date,
        message=None,
        run_type=None,
    ):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        info = {
            "run": run,
            "article_id": article_id,
            "version": version,
            "expanded_folder": expanded_folder,
            "status": status,
            "result": result,
            "message": message,
            "update_date": update_date,
            "requested_action": requested_action,
            "force": force,
            "run_type": run_type,
        }
        self.start_workflow(info)

    def start_workflow(self, info):

        workflow_params = self.get_workflow_params(info)

        self.start_workflow_execution(workflow_params)
