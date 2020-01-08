from workflow.objects import Workflow
from workflow.helper import define_workflow_step


class workflow_S3Monitor(Workflow):

    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100, definition=None):
        super(workflow_S3Monitor, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "S3Monitor"
        self.version = "1.1"
        self.description = "Monitoring an S3 bucket for modifications."
        self.default_execution_start_to_close_timeout = 60 * 25
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        # JSON format workflow definition, for now
        workflow_definition = {
            "name": "S3Monitor",
            "version": "1.1",
            "task_list": self.settings.default_task_list,
            "input": data,

            "start":
                {
                    "requirements": None
                },

            "steps":
                [
                    define_workflow_step("PingWorker", data),
                    define_workflow_step(
                        "S3Monitor", data,
                        heartbeat_timeout=60 * 25,
                        schedule_to_close_timeout=60 * 25,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 25,
                    ),
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
