from workflow.objects import Workflow

"""
CopyGlencoeStillImages workflow
"""

class workflow_CopyGlencoeStillImages(Workflow):

    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        super(workflow_CopyGlencoeStillImages, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "CopyGlencoeStillImages"
        self.version = "1"
        self.description = "Copy Glencoe Still Images workflow"
        self.default_execution_start_to_close_timeout = 60 * 20
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        # JSON format workflow definition, for now
        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,

            "start":
            {
                "requirements": None
            },

            "steps":
            [
                {
                    "activity_type": "PingWorker",
                    "activity_id": "PingWorker",
                    "version": "1",
                    "input": data,
                    "control": None,
                    "heartbeat_timeout": 300,
                    "schedule_to_close_timeout": 300,
                    "schedule_to_start_timeout": 300,
                    "start_to_close_timeout": 300
                },
                {
                    "activity_type": "CopyGlencoeStillImages",
                    "activity_id": "CopyGlencoeStillImages",
                    "version": "1",
                    "input": data,
                    "control": None,
                    "heartbeat_timeout": 60 * 10,
                    "schedule_to_close_timeout": 60 * 20,
                    "schedule_to_start_timeout": 60 * 10,
                    "start_to_close_timeout": 60 * 20
                }
            ],

            "finish":
            {
                "requirements": None
            }
        }

        self.load_definition(workflow_definition)

