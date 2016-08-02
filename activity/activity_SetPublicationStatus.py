import json
import activity
import os
import re
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session
import yaml
from provider.article_structure import ArticleInfo

"""
activity_SetPublicationStatus.py activity
"""
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)


class activity_SetPublicationStatus(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "SetPublicationStatus"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Approve a previously submitted article"
        self.rules = []
        self.info = None
        self.logger = logger
        # TODO : better exception handling

    def do_activity(self, data=None):
        session = Session(self.settings)
        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        run = session.get_value(self.get_workflowId(), 'run')

        self.emit_monitor_event(self.settings, article_id, version, run,
                                "Set Publication Status", "start",
                                "Starting Ending setting of publish status for " + article_id)

        try:
            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)
            eif_filename = session.get_value(self.get_workflowId(), 'eif_filename')
            data = self.get_eif(conn, eif_filename)
            publication_status = self.get_publication_status(data, eif_filename)
            data['publish'] = publication_status
            self.update_bucket(conn, data, eif_filename)

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Set Publication Status", "end",
                                    "Ending setting of publish status for " + article_id)

        except Exception as e:
            self.logger.exception("Exception when setting publication status for " + article_id)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Set Publication Status", "error",
                                    "Error submitting EIF For article" + article_id +
                                    " message:" + e.message)
            return False
        return True

    def update_bucket(self, conn, data, eif_filename):
        json_output = json.dumps(data)
        output_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket
        output_path = eif_filename
        destination = conn.get_bucket(output_bucket)
        destination_key = Key(destination)
        destination_key.key = output_path
        destination_key.set_contents_from_string(json_output)

    def get_eif(self, conn, eif_filename):
        eif_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket
        bucket = conn.get_bucket(eif_bucket)
        key = Key(bucket)
        key.key = eif_filename
        json_input = key.get_contents_as_string()
        data = json.loads(json_input)
        return data

    def get_publication_status(self, data, filename):
        if self.file_of_published_article(filename):
            return True

        settings = self.load_settings()
        publish = False
        override = True
        if settings['default']:
            publish = True
            override = False
            override_rule_keys = settings['override']['hold']
        else:
            override_rule_keys = settings['override']['publish']

        for key in override_rule_keys:
            value = data[key]
            for rule in override_rule_keys[key]:
                if re.search(rule, value):
                    publish = override
        return publish

    def file_of_published_article(self, filename):
        eif_filename_without_path = os.path.basename(filename)
        article_info = ArticleInfo(eif_filename_without_path)
        version = article_info.get_version_from_zip_filename()
        update_date = article_info.get_update_date_from_zip_filename()
        if version != None and update_date != None:
            return True
        return False

    @staticmethod
    def load_settings():
        # load the settings from the YAML file
        stream = file('publication_settings.yaml', 'r')
        formats = yaml.load(stream)
        return formats
