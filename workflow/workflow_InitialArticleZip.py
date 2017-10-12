import workflow

"""
InitialArticleZip workflow
"""


class workflow_InitialArticleZip(workflow.workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "InitialArticleZip"
        self.version = "1"
        self.description = "Initial workflow for article processing"
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
                        "activity_type": "VersionLookup",
                        "activity_id": "VersionLookup",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "VersionReasonDecider",
                        "activity_id": "VersionReasonDecider",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    }
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
