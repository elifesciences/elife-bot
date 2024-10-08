import json
import uuid
from starter.objects import Starter, default_workflow_params
from starter.starter_helper import NullRequiredDataException


class starter_SoftwareHeritageDeposit(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_SoftwareHeritageDeposit, self).__init__(
            settings, logger, "SoftwareHeritageDeposit"
        )

    def get_workflow_params(self, run, info):

        if not info:
            raise NullRequiredDataException(
                "Did not get info in starter %s" % self.name
            )
        for info_key in ["article_id", "input_file"]:
            if info.get(info_key) is None or str(info.get(info_key)) == "":
                raise NullRequiredDataException(
                    "Did not get a %s in starter %s" % (info_key, self.name)
                )

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            str(info.get("article_id")),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 45)

        input_data = info
        input_data["run"] = run
        workflow_params["input"] = json.dumps(input_data, default=lambda ob: None)

        return workflow_params

    def start(self, settings, run, info):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(run, info)

    def start_workflow(self, run=None, info=None):

        if run is None:
            run = str(uuid.uuid4())

        workflow_params = self.get_workflow_params(run, info)
        self.start_workflow_execution(workflow_params)
