import json
from ssl import SSLError
from provider.execution_context import get_session
from provider import github_provider, preprint, utils
from provider.github_provider import RetryException
from provider.utils import settings_environment, unicode_encode
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_PreprintRepository(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PreprintRepository, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "PreprintRepository"
        self.pretty_name = "Update preprint in repository"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Saves/Updates preprint XML on a version control repository"
        self.logger = logger

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_xml_path = session.get_value("article_xml_path")
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        expanded_folder = session.get_value("expanded_folder")

        # assert all Github settings have are not None when live
        # if Github settings are null and we are testing, skip activity
        if None in (
            self.settings.git_preprint_repo_path,
            self.settings.git_repo_name,
            self.settings.github_token,
        ):
            environment = settings_environment(self.settings)
            if environment in ["live", "prod", "end2end"]:
                self.logger.error(
                    (
                        "%s, error updating repository for %s preprint article."
                        " Github settings are unavailable."
                    )
                    % (self.name, version_doi)
                )
                return self.ACTIVITY_PERMANENT_FAILURE
            self.logger.info(
                "%s, skipped as there are no Github "
                "settings (Test enviroment)." % self.name
            )
            return True

        self.logger.info(
            "%s, starting to repository for preprint article %s"
            % (self.name, version_doi)
        )

        # bucket path to the XML file
        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        resource = resource_prefix + "/" + article_xml_path

        # generate XML file name for repo
        xml_file = preprint.PREPRINT_XML_FILE_NAME_PATTERN.format(
            article_id=utils.pad_msid(article_id), version=version
        )
        git_path = self.settings.git_preprint_repo_path + xml_file

        self.logger.info(
            "%s, for %s downloading %s and adding to git repo path %s"
            % (self.name, version_doi, resource, git_path)
        )

        # download xml and commit to git repo
        try:
            storage = storage_context(self.settings)

            file_content = storage.get_resource_as_string(resource)

            message = github_provider.update_github(
                self.settings,
                self.logger,
                git_path,
                unicode_encode(file_content),
            )
            self.logger.info(
                "%s, finished updating repository for article %s. Details: %s"
                % (self.name, version_doi, message)
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
            self.logger.exception(
                "%s, error updating repository for article %s. Details: %s"
                % (self.name, version_doi, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE
