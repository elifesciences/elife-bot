import json

from provider import crossref, lax_provider, outbox_provider, utils
from provider.article_processing import download_jats
from provider.storage_provider import storage_context
from provider.execution_context import get_session
from activity.objects import Activity


class activity_ScheduleCrossrefPeerReview(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ScheduleCrossrefPeerReview, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ScheduleCrossrefPeerReview"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue the article XML for depositing peer reviews to Crossref."
        )
        self.logger = logger
        self.pretty_name = "Schedule Crossref Peer Review"

        # For copying to S3 bucket outbox
        self.crossref_outbox_folder = outbox_provider.outbox_folder(
            "crossref_peer_review"
        )

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        expanded_bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        )
        outbox_bucket_name = self.settings.poa_packaging_bucket

        run = data["run"]
        session = get_session(self.settings, data, run)

        version = session.get_value("version")
        article_id = session.get_value("article_id")
        expanded_folder_name = session.get_value("expanded_folder")

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            self.pretty_name,
            "start",
            "Starting to schedule crossref peer review deposit for " + article_id,
        )

        # if is a silent-correction workflow, only deposit for the most recent article version
        run_type = session.get_value("run_type")
        if run_type == "silent-correction":
            highest_version = lax_provider.article_highest_version(
                article_id, self.settings
            )
            if str(version) != str(highest_version):
                log_message = (
                    "%s will not deposit article %s"
                    + " ingested by silent-correction, its version of %s does not equal the"
                    + " highest version which is %s"
                ) % (self.name, utils.pad_msid(article_id), version, highest_version)
                self.logger.info(log_message)
                self.emit_monitor_event(
                    self.settings,
                    article_id,
                    version,
                    run,
                    self.pretty_name,
                    "end",
                    log_message,
                )
                return True

        # check article XML has <sub-article> tag before queuing it
        if self.xml_sub_article_exists(expanded_folder_name) is False:
            log_message = (
                "%s finds version %s of %s has no sub-article for peer review depositing"
                % (self.name, version, utils.pad_msid(article_id))
            )
            self.logger.info(log_message)
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                log_message,
            )
            return True

        try:
            xml_file_name = lax_provider.get_xml_file_name(
                self.settings, expanded_folder_name, expanded_bucket_name, version
            )

            xml_key_name = expanded_folder_name + "/" + xml_file_name

            new_key_name = self.crossref_outbox_folder + xml_file_name

            self.copy_article_xml_to_outbox(
                dest_bucket_name=outbox_bucket_name,
                new_key_name=new_key_name,
                source_bucket_name=expanded_bucket_name,
                old_key_name=xml_key_name,
            )

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                "Finished scheduling of crossref peer review deposit "
                + article_id
                + " for version "
                + version
                + " run "
                + str(run),
            )

        except Exception as exception:
            self.logger.exception(
                "Exception when scheduling crossref peer review deposit"
            )
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error scheduling crossref peer review deposit "
                + article_id
                + " message:"
                + str(exception),
            )
            return False

        return True

    def xml_sub_article_exists(self, expanded_folder_name):
        jats_file = download_jats(
            self.settings, expanded_folder_name, self.get_tmp_dir(), self.logger
        )
        article_objects = crossref.parse_article_xml([jats_file], self.get_tmp_dir())
        if article_objects and article_objects[0].review_articles:
            return True
        return False

    def copy_article_xml_to_outbox(
        self, dest_bucket_name, new_key_name, source_bucket_name, old_key_name
    ):
        "copy the XML file to an S3 outbox folder, for now"
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + source_bucket_name + "/" + old_key_name
        dest_resource = storage_provider + dest_bucket_name + "/" + new_key_name
        self.logger.info(
            "%s Copying %s to %s " % (self.name, orig_resource, dest_resource)
        )
        storage.copy_resource(orig_resource, dest_resource)
