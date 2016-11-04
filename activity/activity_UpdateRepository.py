import activity
from boto.s3.connection import S3Connection
import tempfile
from github import Github
from github import GithubException
import base64
from S3utility.s3_notification_info import S3NotificationInfo
import requests

"""
activity_UpdateRepository.py activity
"""

class activity_UpdateRepository(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "UpdateRepository"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Saves/Updated the XML on a version control repository"
        self.logger = logger

    def do_activity(self, data=None):
        try:

            info = S3NotificationInfo.from_dict(data)
            s3_file_path = info.file_name

            #connect to bucket
            self.conn = S3Connection(self.settings.aws_access_key_id,
                                 self.settings.aws_secret_access_key,
                                 host=self.settings.s3_hostname)
            bucket = self.conn.get_bucket(self.settings.publishing_buckets_prefix +
                                      self.settings.ppp_cdn_bucket)

            #download xml
            with tempfile.TemporaryFile(mode='r+') as tmp:

                s3_key = bucket.get_key(s3_file_path)
                filename = s3_file_path.split('/')[-1]
                s3_key.get_contents_to_file(tmp)
                file_content = s3_key.get_contents_as_string()
                self.update_github(filename, file_content)


        except Exception as e:
            self.logger.info("Exception in do_activity. data: " + data)
            raise

        return True

    def update_github(self, filename, content):

        g = Github(self.settings.github_token)
        user = g.get_user()
        article_xml_repo = user.get_repo(self.settings.git_repo_name)

        try:
            xml_file = article_xml_repo.get_contents(filename)
        except GithubException as e:
            self.logger.info("GithubException - description: " + e.message)
            self.logger.info("GithubException: file " + filename + " may not exist in github yet. We will try to add it in the repo.")
            response = article_xml_repo.create_file("/" + filename, "Adds XML first time", content)
            self.logger.info("File " + filename + " successfully added. Commit: " + response)
            return

        except Exception as e:
            self.logger.info("Exception: file " + filename + ". Error: " + e.message)
            raise

        try:
            #check for changes first
            if content == xml_file.decoded_content:
                self.logger.info("No changes in file " + filename)
                return

            #there are changes
            response = article_xml_repo.update_file(self.settings.git_repo_path + filename , "Updates xml", content, xml_file.sha)
            self.logger.info("File " + filename + " successfully updated. Commit: " + response)
            return

        except Exception as e:
            self.logger.info("Exception: file " + filename + ". Error: " + e.message)
            raise

