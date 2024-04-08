import json
import os
from provider import preprint, utils
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_GeneratePreprintXml(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_GeneratePreprintXml, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "GeneratePreprintXml"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Generate preprint XML and save it to a bucket folder"
        self.logger = logger
        self.pretty_name = "Generate Preprint XML"

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
        except:
            self.logger.exception("Error starting %s activity" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        session.store_value("run", run)
        # get and store the article data into the session
        article_id = data.get("article_id")
        version = data.get("version")
        self.logger.info("%s, article_id: %s" % (self.name, article_id))
        self.logger.info("%s, version: %s" % (self.name, version))
        session.store_value("article_id", article_id)
        session.store_value("version", version)

        # set the S3 bucket path to hold files
        bucket_folder_name = "preprint.%s.%s/%s" % (article_id, version, run)
        session.store_value("expanded_folder", bucket_folder_name)
        # bucket which holds files
        bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        )

        # generate preprint XML
        xml_file_path = None
        # first check if required settings are available
        if not hasattr(self.settings, "epp_data_bucket"):
            self.logger.info(
                "No epp_data_bucket in settings, skipping %s for article_id %s, version %s"
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.epp_data_bucket:
            self.logger.info(
                (
                    "epp_data_bucket in settings is blank, skipping %s "
                    "for article_id %s, version %s"
                )
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_SUCCESS

        storage = storage_context(self.settings)

        # generate preprint XML file
        try:
            xml_file_path = preprint.generate_preprint_xml(
                self.settings,
                article_id,
                version,
                self.name,
                self.directories,
                self.logger,
            )
        except preprint.PreprintArticleException as exception:
            self.logger.exception(
                (
                    "%s, exception raised generating preprint XML"
                    " for article_id %s version %s: %s"
                )
                % (self.name, article_id, version, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE
        except Exception as exception:
            self.logger.exception(
                (
                    "%s, unhandled exception raised when generating preprint XML"
                    " for article_id %s version %s: %s"
                )
                % (self.name, article_id, version, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # upload XML to the expanded_folder
        filename = xml_file_path.rsplit(os.sep, 1)[-1]
        dest_path = bucket_folder_name + "/" + filename
        storage_resource_dest = (
            self.settings.storage_provider + "://" + bucket_name + "/" + dest_path
        )
        metadata = {"ContentType": utils.content_type_from_file_name(filename)}
        self.logger.info(
            "%s, copying preprint XML %s to %s"
            % (self.name, xml_file_path, storage_resource_dest)
        )
        storage.set_resource_from_filename(
            storage_resource_dest, xml_file_path, metadata
        )

        # Clean up disk
        self.clean_tmp_dir()

        return True
