from provider import docmap_provider
from activity.activity_MecaDetails import activity_MecaDetails


class activity_MecaPostPublicationDetails(activity_MecaDetails):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaPostPublicationDetails, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaPostPublicationDetails"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Collect details about a MECA file to be used in a"
            " post-publication workflow"
        )

    def get_computer_file_url(self, steps, version_doi):
        "return computer_file_url from the docmap for the output MECA"
        return docmap_provider.output_computer_file_url_from_steps(
            steps, version_doi, self.name, self.logger
        )
