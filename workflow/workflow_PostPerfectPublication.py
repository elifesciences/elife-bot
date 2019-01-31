from workflow.objects import Workflow

"""
PostPerfectPublication workflow
"""


class workflow_PostPerfectPublication(Workflow):
    def __init__(self, settings, logger, conn=None, token=None, decision=None,
                 maximum_page_size=100):
        super(workflow_PostPerfectPublication, self).__init__(
            settings, logger, conn, token, decision, maximum_page_size)

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
                        "activity_type": "VerifyPublishResponse",
                        "activity_id": "VerifyPublishResponse",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "ArchiveArticle",
                        "activity_id": "ArchiveArticle",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 15,
                        "schedule_to_close_timeout": 60 * 15,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 15
                    },
                    {
                        "activity_type": "LensArticle",
                        "activity_id": "LensArticle",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60*5,
                        "schedule_to_close_timeout": 60*5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60*5
                    },
                    {
                        "activity_type": "ScheduleDownstream",
                        "activity_id": "ScheduleDownstream",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "UpdateRepository",
                        "activity_id": "UpdateRepository",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "EmailVideoArticlePublished",
                        "activity_id": "EmailVideoArticlePublished",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "PublishDigest",
                        "activity_id": "PublishDigest",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "CreateDigestMediumPost",
                        "activity_id": "CreateDigestMediumPost",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    },
                    {
                        "activity_type": "GeneratePDFCovers",
                        "activity_id": "GeneratePDFCovers",
                        "version": "1",
                        "input": data,
                        "control": None,
                        "heartbeat_timeout": 60 * 5,
                        "schedule_to_close_timeout": 60 * 5,
                        "schedule_to_start_timeout": 300,
                        "start_to_close_timeout": 60 * 5
                    }
                ],

            "finish":
                {
                    "requirements": None
                }
        }

        self.load_definition(workflow_definition)
