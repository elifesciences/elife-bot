import workflow

"""
VersionControl workflow
"""


class workflow_VersionControl(workflow.workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        # (We don't use the timeout values, changing will make no effect to currently registered activities
        #   they are assigned here because it's required)
        self.name = "VersionControl"
        self.version = "1"
        self.description = "Saves/Updates XML in version control repository"
        self.default_execution_start_to_close_timeout = 60 * 5
        self.default_task_start_to_close_timeout = 30

        data = self.get_input()

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
                        "activity_type": "UpdateRepository",
                        "activity_id": "UpdateRepository",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 300,
                        "schedule_to_close_timeout": 300,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 300
                    }
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)