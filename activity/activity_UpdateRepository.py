import activity
from boto.s3.connection import S3Connection
import tempfile
from github import Github
from github import GithubException
import provider.lax_provider as lax_provider
from provider.storage_provider import StorageContext

"""
activity_UpdateRepository.py activity
"""

class RetryException(RuntimeError):
    pass

class activity_UpdateRepository(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

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
            self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                    self.pretty_name, "start",
                                    "Starting Updating repository for article " + data['article_id'])

            # assert all Github settings have are not None when live
            # if Github settings are null and we are testing, skip activity
            if None in (self.settings.git_repo_path, self.settings.git_repo_name, self.settings.github_token):
                import settings as settingsLib
                if isinstance(self.settings(), settingsLib.live) or isinstance(self.settings(), settingsLib.prod) or \
                        isinstance(self.settings(), settingsLib.end2end):
                    self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                            self.pretty_name, "error",
                                            "Error Updating repository for article. Github settings are unavailable.")
                    return activity.activity.ACTIVITY_PERMANENT_FAILURE

                self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                        self.pretty_name, "end",
                                        "UpdateRepository got skipped as there are no Github "
                                        "settings (Test enviroment).")
                return True

            try:

                xml_file = lax_provider.get_xml_file_name(self.settings,
                                                          data['article_id'],
                                                          self.settings.publishing_buckets_prefix +
                                                          self.settings.ppp_cdn_bucket,
                                                          data['version'])
                s3_file_path = data['article_id'] + "/" + xml_file

                #download xml
                with tempfile.TemporaryFile(mode='r+') as tmp:
                    storage_context = StorageContext(self.settings)
                    storage_provider = self.settings.storage_provider + "://"
                    published_bucket = storage_context + self.settings.publishing_buckets_prefix + \
                                       self.settings.ppp_cdn_bucket

                    resource = published_bucket + "/" + s3_file_path

                    storage_provider.get_resource_to_file(resource, tmp)

                    file_content = storage_provider.get_resource_as_string(resource)

                    message = self.update_github(self.settings.git_repo_path + xml_file, file_content)

                    self.logger.info(message)
                    self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                    self.pretty_name, "end",
                                    "Finished Updating repository for article. Details: " + message)
                    return True

            except RetryException as e:
                self.logger.info(e.message)
                return activity.activity.ACTIVITY_TEMPORARY_FAILURE

            except Exception as e:
                self.logger.exception("Exception in do_activity")
                self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                        self.pretty_name, "error",
                                        "Error Updating repository for article. Details: " + str(e))
                return activity.activity.ACTIVITY_PERMANENT_FAILURE



    def update_github(self, repo_file, content):

        g = Github(self.settings.github_token)
        user = g.get_user('elifesciences')
        article_xml_repo = user.get_repo(self.settings.git_repo_name)

        try:
            xml_file = article_xml_repo.get_contents(repo_file)
        except GithubException as e:
            self.logger.info("GithubException - description: " + e.message)
            self.logger.info("GithubException: file " + repo_file + " may not exist in github yet. We will try to add it in the repo.")
            try:
                response = article_xml_repo.create_file(repo_file, "Creates XML", content)
            except GithubException as e:
                self._retry_or_cancel(e)
            return "File " + repo_file + " successfully added. Commit: " + str(response)

        except Exception as e:
            self.logger.info("Exception: file " + repo_file + ". Error: " + e.message)
            raise

        try:
            #check for changes first
            if content == xml_file.decoded_content:
                return "No changes in file " + repo_file

            #there are changes
            try:
                response = article_xml_repo.update_file(repo_file , "Updates xml", content, xml_file.sha)
            except GithubException as e:
                self._retry_or_cancel(e)
            return "File " + repo_file + " successfully updated. Commit: " + str(response)

        except Exception as e:
            self.logger.info("Exception: file " + repo_file + ". Error: " + e.message)
            raise

    def _retry_or_cancel(self, e):
        if e.status == 409:
            self.logger.warning("Retrying because of exception: %s", e)
            raise RetryException(e.message)
        else:
            raise e

