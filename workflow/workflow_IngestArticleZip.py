from workflow.objects import Workflow
from workflow.helper import (
    define_workflow_step, define_workflow_step_short, define_workflow_step_medium)


class workflow_IngestArticleZip(Workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        super(workflow_IngestArticleZip, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "IngestArticleZip"
        self.version = "1"
        self.description = "Process Article XML up to ingestion to Lax (where it's going to be converted to Json)"
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
                    define_workflow_step_medium("VersionLookup", data),
                    define_workflow_step_medium("ExpandArticle", data),
                    define_workflow_step_medium("SendDashboardProperties", data),
                    define_workflow_step_short("ApplyVersionNumber", data),
                    define_workflow_step_medium("VerifyGlencoe", data),
                    define_workflow_step_medium("ConvertImagesToJPG", data),
                    define_workflow_step_medium("DepositIngestAssets", data),
                    define_workflow_step_medium("CopyGlencoeStillImages", data),
                    define_workflow_step("DepositAssets", data),
                    define_workflow_step("InvalidateCdn", data),
                    define_workflow_step_medium("VerifyImageServer", data),
                    define_workflow_step_medium(
                        "VerifyGlencoe", data,
                        activity_id="VerifyGlencoeAgain"),
                    define_workflow_step_short("IngestToLax", data),
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
