import json
import uuid
from starter.starter_helper import NullRequiredDataException
from starter.objects import Starter, default_workflow_params
from provider import utils

"""
Amazon SWF PMCDeposit starter
"""


class starter_PMCDeposit(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_PMCDeposit, self).__init__(settings, logger, "PMCDeposit")

    def get_workflow_params(self, document=None):
        if not document:
            raise NullRequiredDataException(
                "Did not get a document argument. Required."
            )

        workflow_params = default_workflow_params(self.settings)
        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            document.replace("/", "_"),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 60 * 23)

        data = {"document": document}

        info = {
            "run": str(uuid.uuid4()),
            "data": data,
        }

        workflow_params["input"] = json.dumps(info, default=lambda ob: None)
        return workflow_params

    def start(self, settings, document=None):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(document)

    def start_workflow(self, document=None):

        workflow_params = self.get_workflow_params(document)

        self.start_workflow_execution(workflow_params)


if __name__ == "__main__":

    ENV, DOCUMENT = utils.console_start_env_document()
    SETTINGS = utils.get_settings(ENV)

    STARTER = starter_PMCDeposit(SETTINGS)

    STARTER.start_workflow(document=DOCUMENT)
