import json
from provider import utils
from starter.objects import Starter, default_workflow_params
from starter.starter_helper import NullRequiredDataException


class starter_DepositDOAJ(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_DepositDOAJ, self).__init__(settings, logger, "DepositDOAJ")

    def get_workflow_params(self, info):
        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            str(info.get("article_id")),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 15)

        input_data = info
        workflow_params["input"] = json.dumps(input_data, default=lambda ob: None)

        return workflow_params

    def start(self, settings, info):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(info)

    def start_workflow(self, info=None):

        if not info:
            raise NullRequiredDataException(
                "Did not get info in starter %s" % self.name
            )
        for info_key in ["article_id"]:
            if info.get(info_key) is None or str(info.get(info_key)) == "":
                raise NullRequiredDataException(
                    "Did not get a %s in starter %s" % (info_key, self.name)
                )

        self.connect_to_swf()

        workflow_params = self.get_workflow_params(info)

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


if __name__ == "__main__":

    ENV, DOI_ID = utils.console_start_env_doi_id()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_DepositDOAJ()

    INFO = {"article_id": utils.pad_msid(DOI_ID)}

    STARTER.start(settings=SETTINGS, info=INFO)
