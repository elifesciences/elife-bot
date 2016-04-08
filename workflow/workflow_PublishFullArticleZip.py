import workflow

"""
PublishFullArticleZip workflow
"""

class workflow_PublishFullArticleZip(workflow.workflow):

    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

        # SWF Defaults
        self.name = "PublishFullArticleZip"
        self.version = "1"
        self.description = ("Publish full article zip file workflow, unzips and " +
                            "publishes files before PPP workflow is ready")
        self.default_execution_start_to_close_timeout = 60 * 30
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
                    "activity_type": "UnzipFullArticle",
                    "activity_id": "UnzipFullArticle",
                    "version": "1",
                    "input": data,
                    "control": None,
                    "heartbeat_timeout": 60 * 5,
                    "schedule_to_close_timeout": 300,
                    "schedule_to_start_timeout": 60 * 5,
                    "start_to_close_timeout": 60 * 15
                }
            ],

            "finish":
            {
                "requirements": None
            }
        }

        self.load_definition(workflow_definition)

