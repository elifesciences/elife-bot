import json
from provider.execution_context import get_session
from provider import utils
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_ArchivePreprint(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ArchivePreprint, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ArchivePreprint"
        self.pretty_name = "Archive preprint article"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Archive a preprint article post-publication"
        self.logger = logger

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        computer_file_url = session.get_value("computer_file_url")

        self.logger.info(
            "%s, %s copying from computer_file_url %s"
            % (self.name, version_doi, computer_file_url)
        )

        # generate file name for the archive zip file
        current_datetime = utils.get_current_datetime()
        new_zip_file_name = "elife-{article_id}-rp-v{version}-{timestamp}.zip".format(
            article_id=utils.pad_msid(article_id),
            version=version,
            timestamp=current_datetime.strftime("%Y%m%d%H%M%S"),
        )

        self.logger.info(
            "%s, %s new_zip_file_name %s" % (self.name, version_doi, new_zip_file_name)
        )

        bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        )

        # copy the zip to the archive bucket
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        to_resource = storage_provider + bucket_name + "/" + new_zip_file_name
        self.logger.info(
            "%s, %s copying from %s to %s"
            % (self.name, version_doi, computer_file_url, to_resource)
        )
        try:
            storage.copy_resource(computer_file_url, to_resource)
        except Exception as exception:
            self.logger.exception(
                "%s, exception copying resource for article_id %s: %s"
                % (self.name, version_doi, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.clean_tmp_dir()
        return self.ACTIVITY_SUCCESS
