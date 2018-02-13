import workflow

"""
SilentCorrections workflow
"""


class workflow_SilentCorrectionsIngest(workflow.workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "SilentCorrectionsIngest"
        self.version = "1"
        self.description = "Ingests an article to lax as a Silent Correction"
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
                        "activity_type": "VersionDateLookup",
                        "activity_id": "VersionDateLookup",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "ExpandArticle",
                        "activity_id": "ExpandArticle",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "SendDashboardProperties",
                        "activity_id": "SendDashboardProperties",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "ApplyVersionNumber",
                        "activity_id": "ApplyVersionNumber",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 10,
                        "schedule_to_close_timeout": 60 * 10,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 10
                    },
                    {
                        "activity_type": "ModifyArticleSubjects",
                        "activity_id": "ModifyArticleSubjects",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 10,
                        "schedule_to_close_timeout": 60 * 10,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 10
                    },
                    {
                        "activity_type": "VerifyGlencoe",
                        "activity_id": "VerifyGlencoe",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "ConvertImagesToJPG",
                        "activity_id": "ConvertImagesToJPG",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "DepositIngestAssets",
                        "activity_id": "DepositIngestAssets",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "CopyGlencoeStillImages",
                        "activity_id": "CopyGlencoeStillImages",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "VerifyImageServer",
                        "activity_id": "VerifyImageServer",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "IngestToLax",
                        "activity_id": "IngestToLax",
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
