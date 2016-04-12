import json

import activity

from boto.s3.connection import S3Connection

from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import Session
from activity_ConvertJATS import activity_ConvertJATS as ConvertJATS

"""
ScheduleCrossref.py activity
"""

class activity_ScheduleCrossref(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ScheduleCrossref"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Queue the article XML for depositing to Crossref, prior to publication."
        self.logger = logger

        # For copying to crossref outbox from here for now
        self.crossref_outbox_folder = "crossref/outbox/"

    def do_activity(self, data=None):

        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.expanded_bucket_name = (self.settings.publishing_buckets_prefix
                                     + self.settings.expanded_bucket)
        self.crossref_bucket_name = self.settings.poa_packaging_bucket

        info = S3NotificationInfo.from_dict(data)
        session = Session(self.settings)

        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        expanded_folder_name = session.get_value(self.get_workflowId(), 'expanded_folder')
        run = session.get_value(self.get_workflowId(), 'run')

        conn = S3Connection(self.settings.aws_access_key_id,
                            self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(self.expanded_bucket_name)

        try:
            (xml_key, xml_filename) = ConvertJATS.get_article_xml_key(bucket, bucket_folder_name)

            # Rename the XML file to match what is used already
            new_key_name = self.new_crossref_xml_name(
                prefix=self.crossref_outbox_folder,
                journal='elife',
                article_id=str(article_id).zfill(5))

            self.copy_article_xml_to_crossref_outbox(
                new_key_name=new_key_name,
                source_bucket_name=self.expanded_bucket_name,
                old_key_name=xml_key)

            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Crossref",
                                    "end", "Finished scheduling of crossref deposit " + article_id +
                                    " for version " + version + " run " + str(run))
        except Exception as e:
            self.logger.exception("Exception when scheduling crossref")
            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Crossref",
                                    "error", "Error scheduling crossref " + article_id +
                                    " message:" + e.message)
            return False

        return True

    def new_crossref_xml_name(self, prefix, journal, article_id):
        """
        New name we want e.g.: elife99999.xml
        """
        try:
            return prefix + journal + article_id + '.xml'
        except TypeError:
            return None

    def copy_article_xml_to_crossref_outbox(self, new_key_name, source_bucket_name, old_key_name):
        """
        Used for uploading to the crossref outbox, for now
        """
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.crossref_bucket_name)

        key = bucket.copy_key(new_key_name, source_bucket_name, old_key_name)



