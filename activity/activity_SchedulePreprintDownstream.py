import json
import os
from provider import downstream, preprint, utils, yaml_provider
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_SchedulePreprintDownstream(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_SchedulePreprintDownstream, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "SchedulePreprintDownstream"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue a preprint article for depositing to downstream recipients "
            "after the preprint article is published."
        )
        self.logger = logger
        self.pretty_name = "Schedule Preprint Downstream"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        try:
            # get data from the session
            run = data["run"]
            session = get_session(self.settings, data, run)
            article_id = session.get_value("article_id")
            version = session.get_value("version")
            article_xml_path = session.get_value("article_xml_path")
            pdf_url = session.get_value("pdf_url")
            expanded_folder = session.get_value("expanded_folder")
        except:
            self.logger.exception("Error starting %s activity" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info("%s, article_id: %s" % (self.name, article_id))
        self.logger.info("%s, version: %s" % (self.name, version))

        publish_bucket_name = self.settings.poa_packaging_bucket

        rules = yaml_provider.load_config(self.settings)

        status = "preprint"
        first_by_status = bool(int(version) == 1)
        run_type = data.get("run_type")

        try:
            source_xml_key_name = expanded_folder + "/" + article_xml_path
            expanded_bucket_name = self.settings.bot_bucket
            # new name for the file
            xml_file_name = preprint.PREPRINT_XML_FILE_NAME_PATTERN.format(
                article_id=utils.pad_msid(article_id), version=version
            )

            outbox_list = downstream.choose_outboxes(
                status, first_by_status, rules, run_type, pdf_url=pdf_url
            )

            for outbox in outbox_list:
                self.copy_article_xml_to_outbox(
                    publish_bucket_name,
                    xml_file_name,
                    expanded_bucket_name,
                    source_xml_key_name,
                    outbox,
                )

            self.logger.info(
                (
                    "%s, finished scheduling of downstream deposits for"
                    " preprint article_id %s, version %s"
                )
                % (self.name, article_id, version)
            )

        except Exception as exception:
            self.logger.exception(
                (
                    "%s, exception when scheduling downstream deposits for"
                    " preprint article_id %s, version %s: %s"
                )
                % (self.name, article_id, version, str(exception))
            )

            return self.ACTIVITY_TEMPORARY_FAILURE

        # Clean up disk
        self.clean_tmp_dir()

        return self.ACTIVITY_SUCCESS

    def copy_article_xml_to_outbox(
        self,
        dest_bucket_name,
        new_key_name,
        source_bucket_name,
        old_key_name,
        prefix,
    ):
        "copy the XML file to an S3 outbox folder, for now"
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + source_bucket_name + "/" + old_key_name
        dest_resource = (
            storage_provider + dest_bucket_name + "/" + prefix + new_key_name
        )
        self.logger.info(
            "ScheduleDownstream Copying %s to %s " % (orig_resource, dest_resource)
        )
        storage.copy_resource(orig_resource, dest_resource)
