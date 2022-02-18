import json
from S3utility.s3_notification_info import S3NotificationInfo
from starter.objects import Starter, default_workflow_params
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF SilentCorrectionsIngest starter, preparing article xml for lax.
"""


class starter_SilentCorrectionsIngest(Starter):
    def __init__(self, settings=None, logger=None):
        super(starter_SilentCorrectionsIngest, self).__init__(
            settings, logger, "SilentCorrectionsIngest"
        )

    def get_workflow_params(self, run, info):
        workflow_params = default_workflow_params(self.settings)

        if hasattr(info, "file_name") is False or info.file_name is None:
            raise NullRequiredDataException("filename is Null. Did not get a filename.")

        workflow_params["workflow_id"] = "%s_%s" % (
            self.name,
            info.file_name.replace("/", "_"),
        )
        workflow_params["workflow_name"] = self.name
        workflow_params["workflow_version"] = "1"
        workflow_params["execution_start_to_close_timeout"] = str(60 * 60)

        input_data = S3NotificationInfo.to_dict(info)
        input_data["run"] = run
        input_data["version_lookup_function"] = "article_highest_version"
        input_data["run_type"] = "silent-correction"
        input_data["force"] = True

        workflow_params["input"] = json.dumps(input_data, default=lambda ob: None)

        return workflow_params

    def start(self, settings, run=None, info=None):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(run, info)

    def start_workflow(self, run, info):

        workflow_params = self.get_workflow_params(run, info)

        self.start_workflow_execution(workflow_params)
