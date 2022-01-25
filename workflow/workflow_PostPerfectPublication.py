from workflow.objects import Workflow
from workflow.helper import define_workflow_step, define_workflow_step_medium


class workflow_PostPerfectPublication(Workflow):
    def __init__(
        self,
        settings,
        logger,
        client=None,
        token=None,
        decision=None,
        maximum_page_size=100,
    ):
        super(workflow_PostPerfectPublication, self).__init__(
            settings, logger, client, token, decision, maximum_page_size
        )

        # SWF Defaults
        self.name = "PostPerfectPublication"
        self.version = "1"
        self.description = "Perform post-publication tasks for an article"
        self.default_execution_start_to_close_timeout = 60 * 5
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,
            "start": {"requirements": None},
            "steps": [
                define_workflow_step("PingWorker", data),
                define_workflow_step("VerifyPublishResponse", data),
                define_workflow_step_medium("ArchiveArticle", data),
                define_workflow_step("LensArticle", data),
                define_workflow_step("ScheduleDownstream", data),
                define_workflow_step("UpdateRepository", data),
                define_workflow_step("EmailVideoArticlePublished", data),
                define_workflow_step("PublishDigest", data),
                define_workflow_step("CreateDigestMediumPost", data),
                define_workflow_step("GeneratePDFCovers", data),
                define_workflow_step("DepositDOAJ", data),
            ],
            "finish": {"requirements": None},
        }

        self.load_definition(workflow_definition)
