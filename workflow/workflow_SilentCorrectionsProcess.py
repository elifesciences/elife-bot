import workflow

"""
SilentCorrectionsProcess workflow
"""


class workflow_SilentCorrectionsProcess(workflow.workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

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
                        "activity_type": "VerifyLaxResponse",
                        "activity_id": "VerifyLaxResponse",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "ScheduleCrossref",
                        "activity_id": "ScheduleCrossref",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "ConvertJATS",
                        "activity_id": "ConvertJATS",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "SetPublicationStatus",
                        "activity_id": "SetPublicationStatus",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "ResizeImages",
                        "activity_id": "ResizeImages",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 30,
                        "schedule_to_close_timeout": 60 * 30,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 30
                    },
                    {
                        "activity_type": "DepositAssets",
                        "activity_id": "DepositAssets",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "CopyGlencoeStillImages",
                        "activity_id": "CopyGlencoeStillImages",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                       "activity_type": "VerifyImageServer",
                       "activity_id": "VerifyImageServer",
                       "version": "1",
                       "input": data,
                       "control": None,
                       "heartbeat_timeout": 60 * 5,
                       "schedule_to_close_timeout": 60 * 5,
                       "schedule_to_start_timeout": 300,
                       "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "SetEIFPublish",
                        "activity_id": "SetEIFPublish",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "PreparePostEIF",
                        "activity_id": "PreparePostEIF",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "PublishToLax",
                        "activity_id": "PublishToLax",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },

                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
