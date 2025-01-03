from ssl import SSLError
import tempfile
from github import Github
from github import GithubException
from provider.utils import pad_msid, settings_environment, unicode_encode
import provider.lax_provider
from provider.storage_provider import storage_context
from activity.objects import Activity

"""
activity_UpdateRepository.py activity
"""


class RetryException(RuntimeError):
    pass


class activity_UpdateRepository(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_UpdateRepository, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "UpdateRepository"
        self.pretty_name = "Update Repository"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Saves/Updated the XML on a version control repository"
        self.logger = logger

    def do_activity(self, data=None):
        self.emit_monitor_event(
            self.settings,
            data["article_id"],
            data["version"],
            data["run"],
            self.pretty_name,
            "start",
            "Starting Updating repository for article " + data["article_id"],
        )

        # assert all Github settings have are not None when live
        # if Github settings are null and we are testing, skip activity
        if None in (
            self.settings.git_repo_path,
            self.settings.git_repo_name,
            self.settings.github_token,
        ):
            environment = settings_environment(self.settings)
            if environment in ["live", "prod", "end2end"]:
                self.emit_monitor_event(
                    self.settings,
                    data["article_id"],
                    data["version"],
                    data["run"],
                    self.pretty_name,
                    "error",
                    "Error Updating repository for article. Github settings are unavailable.",
                )
                return self.ACTIVITY_PERMANENT_FAILURE

            self.emit_monitor_event(
                self.settings,
                data["article_id"],
                data["version"],
                data["run"],
                self.pretty_name,
                "end",
                "UpdateRepository got skipped as there are no Github "
                "settings (Test enviroment).",
            )
            return True

        try:

            xml_file = provider.lax_provider.get_xml_file_name(
                self.settings,
                pad_msid(data["article_id"]),
                self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket,
                data["version"],
            )
            s3_file_path = pad_msid(data["article_id"]) + "/" + xml_file

            storage = storage_context(self.settings)
            bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
            )

            # download xml
            with tempfile.TemporaryFile(mode="w+b") as tmp:
                storage_provider = self.settings.storage_provider + "://"
                published_path = storage_provider + bucket_name

                resource = published_path + "/" + s3_file_path

                storage.get_resource_to_file(resource, tmp)

                file_content = storage.get_resource_as_string(resource)

                message = self.update_github(
                    self.settings.git_repo_path + xml_file, unicode_encode(file_content)
                )
                self.logger.info(message)
                self.emit_monitor_event(
                    self.settings,
                    data["article_id"],
                    data["version"],
                    data["run"],
                    self.pretty_name,
                    "end",
                    "Finished Updating repository for article. Details: " + message,
                )
                return True

        except RetryException as exception:
            self.logger.info(str(exception))
            return self.ACTIVITY_TEMPORARY_FAILURE

        except SSLError as exception:
            # python 3 support for comparing exception message
            strip_characters = "'(),"
            exception_message = (
                str(exception).lstrip(strip_characters).rstrip(strip_characters)
            )
            if exception_message == "The read operation timed out":
                self.logger.info(str(exception))
                return self.ACTIVITY_TEMPORARY_FAILURE

            self.logger.exception("Exception in do_activity")
            return self.ACTIVITY_PERMANENT_FAILURE

        except Exception as exception:
            self.logger.exception("Exception in do_activity")
            self.emit_monitor_event(
                self.settings,
                data["article_id"],
                data["version"],
                data["run"],
                self.pretty_name,
                "error",
                "Error Updating repository for article. Details: " + str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

    def update_github(self, repo_file, content):

        github_object = Github(self.settings.github_token)
        user = github_object.get_user("elifesciences")
        article_xml_repo = user.get_repo(self.settings.git_repo_name)

        try:
            xml_file = article_xml_repo.get_contents(repo_file)
        except GithubException as exception:
            self.logger.info("GithubException - description: " + str(exception))
            self.logger.info(
                "GithubException: file "
                + repo_file
                + " may not exist in github yet. We will try to add it in the repo."
            )
            try:
                response = article_xml_repo.create_file(
                    repo_file, "Creates XML", content
                )
            except GithubException as inner_exception:
                self._retry_or_cancel(inner_exception)
            return "File " + repo_file + " successfully added. Commit: " + str(response)

        except Exception as exception:
            self.logger.info(
                "Exception: file " + repo_file + ". Error: " + str(exception)
            )
            raise

        try:
            # check for changes first
            if content == xml_file.decoded_content:
                return "No changes in file " + repo_file

            # there are changes
            try:
                response = article_xml_repo.update_file(
                    repo_file, "Updates xml", content, xml_file.sha
                )
            except GithubException as exception:
                self._retry_or_cancel(exception)
            return (
                "File " + repo_file + " successfully updated. Commit: " + str(response)
            )

        except Exception as exception:
            self.logger.info(
                "Exception: file " + repo_file + ". Error: " + str(exception)
            )
            raise

    def _retry_or_cancel(self, exception):
        if exception.status == 409:
            self.logger.warning("Retrying because of exception: %s" % exception)
            raise RetryException(str(exception))

        raise exception
