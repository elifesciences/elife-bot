import shutil
import datetime
import os
import re
import botocore
import dashboard_queue
from provider import cleaner, downstream, outbox_provider, utils

"""
Amazon SWF activity base class
"""


class Activity:

    ACTIVITY_SUCCESS = "ActivitySuccess"
    ACTIVITY_TEMPORARY_FAILURE = "ActivityTemporaryFailure"
    ACTIVITY_PERMANENT_FAILURE = "ActivityPermanentFailure"
    ACTIVITY_EXIT_WORKFLOW = "ActivityExitWorkflow"

    # Base class
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        self.settings = settings
        self.logger = logger
        self.result = None
        self.token = token
        self.activity_task = activity_task
        # boto3 swf client
        self.client = client

        # SWF Defaults, most are set in derived classes or at runtime
        try:
            self.domain = self.settings.domain
        except AttributeError:
            self.domain = None

        try:
            self.task_list = self.settings.default_task_list
        except AttributeError:
            self.task_list = None

        self.name = None
        self.pretty_name = None
        self.version = None
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 10
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = None

        self.tmp_base_dir = "tmp"
        self.tmp_dir = None
        self.directories = None

    def describe(self):
        """
        Describe activity type from SWF, to confirm it exists
        Requires object to have an SWF client using boto3
        """
        if (
            self.client is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        activity_type = {"name": self.name, "version": self.version}

        try:
            response = self.client.describe_activity_type(
                domain=self.domain, activityType=activity_type
            )
        except botocore.exceptions.ClientError:
            response = None

        return response

    def register(self):
        """
        Register the activity type with SWF, if it does not already exist
        Requires object to have an SWF client using boto3
        """
        if (
            self.client is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        if self.describe() is None:
            response = self.client.register_activity_type(
                domain=str(self.domain),
                name=str(self.name),
                version=str(self.version),
                description=str(self.description),
                defaultTaskStartToCloseTimeout=str(
                    self.default_task_start_to_close_timeout
                ),
                defaultTaskHeartbeatTimeout=str(self.default_task_heartbeat_timeout),
                defaultTaskList={"name": str(self.task_list)},
                defaultTaskScheduleToStartTimeout=str(
                    self.default_task_schedule_to_start_timeout
                ),
                defaultTaskScheduleToCloseTimeout=str(
                    self.default_task_schedule_to_close_timeout
                ),
            )

            return response

    def get_workflowId(self):
        """
        Get the workflowId from the SWF activity_task
        if it is available
        """
        workflowId = None
        if self.activity_task is None:
            return None

        try:
            workflowId = self.activity_task["workflowExecution"]["workflowId"]
        except KeyError:
            workflowId = None

        return workflowId

    def get_activityId(self):
        """
        Get the activityId from the SWF activity_task
        if it is available
        """
        activityId = None
        if self.activity_task is None:
            return None

        try:
            activityId = self.activity_task["activityId"]
        except KeyError:
            activityId = None

        return activityId

    def make_tmp_dir(self):
        """
        Check or create temporary directory for this activity
        """
        # Try and make the based tmp directory, if it does not exist
        if self.tmp_base_dir:
            try:
                os.mkdir(self.tmp_base_dir)
            except OSError:
                pass

        # Create a new directory specifically for this activity
        dir_name = datetime.datetime.utcnow().strftime("%Y-%m-%d.%H.%M.%S")
        workflowId = self.get_workflowId()
        activityId = self.get_activityId()
        try:
            domain = self.settings.domain
        except:
            domain = None
        if domain:
            # Use regular expression to strip out messy symbols
            domain_safe = re.sub(r"\W", "", domain)
            dir_name += "." + domain_safe
        if workflowId:
            # Use regular expression to strip out messy symbols
            workflowId_safe = re.sub(r"\W", "", workflowId)
            dir_name += "." + workflowId_safe
        if activityId:
            # Use regular expression to strip out messy symbols
            activityId_safe = re.sub(r"\W", "", activityId)
            dir_name += "." + activityId_safe

        if self.tmp_base_dir:
            full_dir_name = self.tmp_base_dir + os.sep + dir_name
        else:
            full_dir_name = dir_name

        try:
            os.mkdir(full_dir_name)
            self.tmp_dir = full_dir_name
        except OSError:
            # Directory may already exist, happens when running tests, check if it exists
            if os.path.isdir(full_dir_name):
                self.tmp_dir = full_dir_name

        if not self.tmp_dir:
            raise RuntimeError("Cannot create temporary directory %s" % full_dir_name)

    def get_tmp_dir(self):
        """
        Get the temporary file directory, but if not set
        then make the directory
        """
        if self.tmp_dir:
            return self.tmp_dir

        self.make_tmp_dir()

        return self.tmp_dir

    def make_activity_directories(self, dir_names=None):
        """
        Create the directories in the activity tmp_dir
        """
        if not dir_names and self.directories and hasattr(self.directories, "values"):
            dir_names = list(self.directories.values())
        if not dir_names:
            self.logger.info("No dir_names to create in make_activity_directories()")
            return None
        # Now try to find or make directories
        for dir_name in dir_names:
            if os.path.isdir(dir_name):
                # directory exists, continue
                continue
            try:
                os.mkdir(dir_name)
            except OSError as exception:
                self.logger.exception(str(exception))
                raise
        return True

    def clean_tmp_dir(self):

        tmp_dir = self.get_tmp_dir()
        shutil.rmtree(tmp_dir)
        self.tmp_dir = None

    def emit_activity_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                status,
                message,
            )
            return True
        except Exception as exception:
            self.logger.exception(
                "Exception emitting %s message. Details: %s"
                % (str(status), str(exception))
            )
        return None

    def message_activity_name(self):
        "the name for the activity to use in emit messages"
        if self.pretty_name:
            return str(self.pretty_name)
        return str(self.name)

    def emit_activity_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_activity_message(
            article_id,
            version,
            run,
            "start",
            "Starting " + self.message_activity_name() + " for " + str(article_id),
        )

    def emit_activity_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_activity_message(
            article_id,
            version,
            run,
            "end",
            "Finished " + self.message_activity_name() + " for " + str(article_id),
        )

    @staticmethod
    def emit_monitor_event(
        settings, item_identifier, version, run, event_type, status, message
    ):
        message = dashboard_queue.build_event_message(
            utils.pad_msid(item_identifier),
            version,
            run,
            event_type,
            datetime.datetime.now(),
            status,
            message,
        )

        dashboard_queue.send_message(message, settings)

    @staticmethod
    def set_monitor_property(
        settings, item_identifier, name, value, property_type, version=0
    ):
        message = dashboard_queue.build_property_message(
            utils.pad_msid(item_identifier), version, name, value, property_type
        )
        dashboard_queue.send_message(message, settings)

    def s3_bucket_folder(self, workflow_name):
        "get the S3 bucket folder from YAML file for outbox folders"
        rules = downstream.load_config(self.settings)
        downstream_workflow_map = downstream.workflow_s3_bucket_folder_map(rules)
        return outbox_provider.workflow_foldername(
            workflow_name, downstream_workflow_map
        )

    def get_docmap_string(self, article_id, identifier):
        # generate docmap URL
        docmap_url = cleaner.docmap_url(self.settings, article_id)
        self.logger.info("%s, docmap_url: %s" % (self.name, docmap_url))

        # get docmap json
        self.logger.info(
            "%s, getting docmap_string for identifier: %s"
            % (self.name, identifier)
        )
        return cleaner.get_docmap_by_account_id(
            docmap_url, self.settings.docmap_account_id
        )


class CleanerBaseActivity(Activity):
    "activity class to use cleaner provider logging"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super().__init__(settings, logger, client, token, activity_task)
        # Track logging values
        self.activity_log_file = "cleaner.log"
        self.log_file_path = None
        self.cleaner_log_handers = []

    def start_cleaner_log(self):
        "configure the cleaner provider log file handler"
        self.log_file_path = os.path.join(self.get_tmp_dir(), self.activity_log_file)
        if self.log_file_path not in self.cleaner_log_handers:
            self.cleaner_log_handers = cleaner.configure_activity_log_handlers(
                self.log_file_path
            )

    def end_cleaner_log(self, session):
        "close cleaner provider log file handler and optionally save the contents to the session"
        # remove the log handlers
        for log_handler in self.cleaner_log_handers:
            cleaner.log_remove_handler(log_handler)

        # read the cleaner log contents
        with open(self.log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()

        # add the log_contents to the session variable
        if session:
            cleaner_log = session.get_value("cleaner_log")
            if cleaner_log is None:
                cleaner_log = log_contents
            else:
                cleaner_log += log_contents
            session.store_value("cleaner_log", cleaner_log)


class AcceptedBaseActivity(CleanerBaseActivity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super().__init__(settings, logger, client, token, activity_task)
        # Track some values
        self.input_file = None
        # stubs
        self.directories = {}
        self.statuses = {}

    def read_session(self, session):
        "basic session values"
        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")
        article_id = session.get_value("article_id")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )
        return expanded_folder, input_filename, article_id

    def bucket_asset_file_name_map(self, expanded_folder):
        "get list of bucket objects from expanded folder"
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        self.logger.info(
            "%s, asset_file_name_map: %s" % (self.name, asset_file_name_map)
        )
        return asset_file_name_map

    def download_xml_file_from_bucket(self, asset_file_name_map):
        "find S3 object for article XML and download it"
        xml_file_path = cleaner.download_xml_file_from_bucket(
            self.settings,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )
        return xml_file_path

    def upload_xml_file_to_bucket(self, asset_file_name_map, expanded_folder, storage):
        "upload the XML to the bucket"
        upload_key = cleaner.article_xml_asset(asset_file_name_map)[0]
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
            + "/"
            + upload_key
        )
        local_file_path = asset_file_name_map.get(upload_key)
        storage.set_resource_from_filename(s3_resource, local_file_path)
        self.logger.info(
            "%s, uploaded %s to S3 object: %s"
            % (self.name, local_file_path, s3_resource)
        )
        self.statuses["upload_xml"] = True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )

    def clean_tmp_dir(self):
        "custom cleaning of temp directory in order to retain some files for debugging purposes"
        keep_dirs = []
        for dir_name, dir_path in self.directories.items():
            if dir_name in keep_dirs or not os.path.exists(dir_path):
                continue
            shutil.rmtree(dir_path)

    def rewrite_file_tags(self, xml_file_path, file_transformations, input_filename):
        "modify the XML file tags"
        if file_transformations:
            try:
                cleaner.xml_rewrite_file_tags(
                    xml_file_path, file_transformations, input_filename
                )
                self.logger.info(
                    "%s, %s file_transformations rewriting XML completed"
                    % (self.name, input_filename)
                )
                return True
            except:
                log_message = (
                    "%s, exception invoking xml_rewrite_file_tags for file %s"
                    % (
                        self.name,
                        input_filename,
                    )
                )
                self.logger.exception(log_message)
        return None

    def remove_file_tags(self, xml_root, file_name_list, input_filename):
        "remove XML file tags"
        files_tag = xml_root.find("./front/article-meta/files")
        if files_tag:
            for file_tag in files_tag.findall("file"):
                file_nm_tag = file_tag.find("upload_file_nm")
                if (
                    file_nm_tag is not None
                    and file_nm_tag.text
                    and file_nm_tag.text in file_name_list
                ):
                    self.logger.info(
                        "removing file tag for %s in file %s"
                        % (file_nm_tag.text, input_filename)
                    )
                    files_tag.remove(file_tag)

            return True
        return None

    def rename_expanded_folder_files(
        self, asset_file_name_map, expanded_folder, file_transformations, storage
    ):
        "rename objects in the S3 bucket expanded folder"
        # map values without folder names to match them later
        asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}
        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        for file_transform in file_transformations:
            if not file_transform[0].xml_name or not file_transform[1].xml_name:
                log_message = ("%s, copying to %s, a blank value cannot be copied, old xml_name %s to new xml_name %s"
                % (self.name, resource_prefix, file_transform[0].xml_name, file_transform[1].xml_name))
                raise RuntimeError(log_message)
                self.logger.exception(
                    log_message
                )
                continue
            old_s3_resource = (
                resource_prefix + "/" + asset_key_map.get(file_transform[0].xml_name)
            )
            # get the subfolder of the old resource to prepend to the new resource
            new_resource_subfolder = old_s3_resource.rsplit(resource_prefix, 1)[
                -1
            ].rsplit("/", 1)[0]
            new_s3_resource = (
                resource_prefix
                + new_resource_subfolder
                + "/"
                + file_transform[1].xml_name
            )
            # copy old key to new key
            self.logger.info(
                "%s, copying old S3 key %s to %s"
                % (self.name, old_s3_resource, new_s3_resource)
            )
            storage.copy_resource(old_s3_resource, new_s3_resource)
            # delete old key
            self.logger.info(
                "%s, deleting old S3 key %s" % (self.name, old_s3_resource)
            )
            storage.delete_resource(old_s3_resource)
        return True

    def delete_expanded_folder_files(
        self, asset_file_name_map, expanded_folder, file_name_list, storage
    ):
        "delete objects from the S3 bucket expanded folder"
        asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}
        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        for file_name in file_name_list:
            old_s3_resource = resource_prefix + "/" + asset_key_map.get(file_name)
            # delete old key
            self.logger.info(
                "%s, deleting old S3 key %s" % (self.name, old_s3_resource)
            )
            storage.delete_resource(old_s3_resource)
