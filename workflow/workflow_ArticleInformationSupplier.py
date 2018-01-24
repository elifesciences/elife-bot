import workflow

"""
ArticleInformationSupplier workflow
"""


class workflow_ArticleInformationSupplier(workflow.workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "ArticleInformationSupplier"
        self.version = "1"
        self.description = "Supplies information to next workflow after successfully posting EIF"
        self.default_execution_start_to_close_timeout = 60 * 5
        self.default_task_start_to_close_timeout = 30

        # Get the input from the JSON decision response
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
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)