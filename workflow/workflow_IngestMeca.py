from workflow.objects import Workflow
from workflow.helper import define_workflow_step


class workflow_IngestMeca(Workflow):
    def __init__(
        self,
        settings,
        logger,
        client=None,
        token=None,
        decision=None,
        maximum_page_size=100,
    ):
        super(workflow_IngestMeca, self).__init__(
            settings, logger, client, token, decision, maximum_page_size
        )

        # SWF Defaults
        self.name = "IngestMeca"
        self.version = "1"
        self.description = "Ingest preprint MECA file and modify it"
        self.default_execution_start_to_close_timeout = 60 * 15
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
        data = self.get_input()

        # JSON format workflow definition, for now
        workflow_definition = {
            "name": self.name,
            "version": self.version,
            "task_list": self.settings.default_task_list,
            "input": data,
            "start": {"requirements": None},
            "steps": [
                define_workflow_step("PingWorker", data),
                define_workflow_step("MecaDetails", data),
                define_workflow_step("ExpandMeca", data),
                define_workflow_step("ModifyMecaFiles", data),
                define_workflow_step("ModifyMecaXml", data),
                define_workflow_step("MecaPeerReviews", data),
                define_workflow_step("MecaPeerReviewImages", data),
                define_workflow_step("MecaPeerReviewFigs", data),
                define_workflow_step("MecaPeerReviewTables", data),
                define_workflow_step("MecaPeerReviewEquations", data),
                define_workflow_step("MecaXslt", data),
                define_workflow_step("ValidateJatsDtd", data),
                define_workflow_step("ValidatePreprintSchematron", data),
                define_workflow_step("OutputMeca", data),
                define_workflow_step("EmailMecaOutput", data),
            ],
            "finish": {"requirements": None},
        }

        self.load_definition(workflow_definition)
