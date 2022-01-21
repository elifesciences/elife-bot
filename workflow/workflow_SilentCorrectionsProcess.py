from workflow.objects import Workflow
from workflow.helper import define_workflow_step


class workflow_SilentCorrectionsProcess(Workflow):
    def __init__(
        self,
        settings,
        logger,
        conn=None,
        token=None,
        decision=None,
        maximum_page_size=100,
        client=None,
    ):
        super(workflow_SilentCorrectionsProcess, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size, client=client
        )

        # SWF Defaults
        self.name = "SilentCorrectionsProcess"
        self.version = "1"
        self.description = "Process JATS zip article as Silent Correction"
        self.default_execution_start_to_close_timeout = 60 * 5
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        # JSON format workflow definition, for now - may be from common YAML definition
        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,
            "start": {"requirements": None},
            "steps": [
                define_workflow_step("PingWorker", data),
                define_workflow_step("VerifyLaxResponse", data),
                define_workflow_step("ScheduleCrossref", data),
                define_workflow_step("ScheduleCrossrefPeerReview", data),
                define_workflow_step("IngestDigestToEndpoint", data),
                define_workflow_step("PublishToLax", data),
            ],
            "finish": {"requirements": None},
        }

        self.load_definition(workflow_definition)
