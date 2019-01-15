from workflow.objects import Workflow

"""
PMCDeposit workflow
"""

class workflow_PMCDeposit(Workflow):

    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        super(workflow_PMCDeposit, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "PMCDeposit"
        self.version = "1"
        self.description = "Deposit article files to PMC"
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
                    "activity_type": "PMCDeposit",
                    "activity_id": "PMCDeposit",
                    "version": "1",
                    "input": data,
                    "control": None,
                    "heartbeat_timeout": 60 * 30,
                    "schedule_to_close_timeout": 60 * 120,
                    "schedule_to_start_timeout": 300,
                    "start_to_close_timeout": 60 * 120
                }
            ],

            "finish":
            {
                "requirements": None
            }
        }

        self.load_definition(workflow_definition)

