from workflow.objects import Workflow
from workflow.helper import define_workflow_step


class workflow_FindNewDocmaps(Workflow):
    def __init__(
        self,
        settings,
        logger,
        client=None,
        token=None,
        decision=None,
        maximum_page_size=100,
    ):
        super(workflow_FindNewDocmaps, self).__init__(
            settings, logger, client, token, decision, maximum_page_size
        )

        # SWF Defaults
        self.name = "FindNewDocmaps"
        self.version = "1"
        self.description = "Find modified docmaps for preprint versions"
        self.default_execution_start_to_close_timeout = 60 * 15
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        # JSON format workflow definition, for now
        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,
            "start": {"requirements": None},
            "steps": [
                define_workflow_step("PingWorker", data),
                define_workflow_step("FindNewDocmaps", data),
            ],
            "finish": {"requirements": None},
        }

        self.load_definition(workflow_definition)
