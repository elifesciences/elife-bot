from workflow.objects import Workflow
from workflow.helper import define_workflow_step, define_workflow_step_medium


class workflow_PostPreprintPublication(Workflow):
    def __init__(
        self,
        settings,
        logger,
        client=None,
        token=None,
        decision=None,
        maximum_page_size=100,
    ):
        super(workflow_PostPreprintPublication, self).__init__(
            settings, logger, client, token, decision, maximum_page_size
        )

        # SWF Defaults
        self.name = "PostPreprintPublication"
        self.version = "1"
        self.description = "Post-publication tasks for a preprint article"
        self.default_execution_start_to_close_timeout = 60 * 5
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,
            "start": {"requirements": None},
            "steps": [
                define_workflow_step("PingWorker", data),
                define_workflow_step("MecaPostPublicationDetails", data),
                define_workflow_step(
                    "ExpandMeca",
                    data,
                    heartbeat_timeout=60 * 10,
                    schedule_to_close_timeout=60 * 10,
                    schedule_to_start_timeout=30,
                    start_to_close_timeout=60 * 10,
                ),
                define_workflow_step("ModifyMecaPublishedXml", data),
                define_workflow_step("GeneratePreprintXml", data),
                define_workflow_step("ScheduleCrossrefPreprint", data),
                define_workflow_step("SchedulePreprintDownstream", data),
                define_workflow_step(
                    "OutputMeca",
                    data,
                    heartbeat_timeout=60 * 10,
                    schedule_to_close_timeout=60 * 10,
                    schedule_to_start_timeout=30,
                    start_to_close_timeout=60 * 10,
                ),
                define_workflow_step("FindPreprintPDF", data),
                define_workflow_step("ConfirmPreprintPDF", data),
            ],
            "finish": {"requirements": None},
        }

        self.load_definition(workflow_definition)
