from workflow.objects import Workflow
from workflow.helper import define_workflow_step


class workflow_SilentCorrectionsIngest(Workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        super(workflow_SilentCorrectionsIngest, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

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
                    define_workflow_step("PingWorker", data),
                    define_workflow_step(
                        "VersionLookup", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step(
                        "VersionDateLookup", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step(
                        "ExpandArticle", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step("SendDashboardProperties", data),
                    define_workflow_step(
                        "ApplyVersionNumber", data,
                        heartbeat_timeout=60 * 10,
                        schedule_to_close_timeout=60 * 10,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 10,
                    ),
                    define_workflow_step("ModifyArticleSubjects", data),
                    define_workflow_step(
                        "VerifyGlencoe", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step(
                        "ConvertImagesToJPG", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step(
                        "DepositIngestAssets", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step(
                        "CopyGlencoeStillImages", data,
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step("DepositAssets", data),
                    define_workflow_step("InvalidateCdn", data),
                    define_workflow_step(
                        "VerifyGlencoe", data,
                        activity_id="VerifyGlencoeAgain",
                        heartbeat_timeout=60 * 15,
                        schedule_to_close_timeout=60 * 15,
                        schedule_to_start_timeout=60 * 5,
                        start_to_close_timeout=60 * 15,
                    ),
                    define_workflow_step("IngestToLax", data),
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
