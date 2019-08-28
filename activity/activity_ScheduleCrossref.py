import json

from boto.s3.connection import S3Connection
from provider import lax_provider
from provider.execution_context import get_session
from provider.article_structure import get_article_xml_key
from activity.objects import Activity

"""
ScheduleCrossref.py activity
"""

class activity_ScheduleCrossref(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ScheduleCrossref, self).__init__(
            settings, logger, conn, token, activity_task)

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

        run = data['run']
        session = get_session(self.settings, data, run)

        version = session.get_value('version')
        article_id = session.get_value('article_id')
        expanded_folder_name = session.get_value('expanded_folder')

        # if is a silent-correction workflow, only deposit for the most recent article version
        run_type = session.get_value("run_type")
        if run_type == "silent-correction":
            highest_version = lax_provider.article_highest_version(article_id, self.settings)
            if str(version) != str(highest_version):
                self.logger.info(
                    'ScheduleCrossref will not deposit article %s' +
                    ' ingested by silent-correction, its version of %s does not equal the' +
                    ' highest version is %s', (article_id, version, highest_version))
                return True

        conn = S3Connection(self.settings.aws_access_key_id,
                            self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(self.expanded_bucket_name)

        self.emit_monitor_event(self.settings, article_id, version, run,
                                "Schedule Crossref", "start",
                                "Starting scheduling of crossref deposit for " + article_id)

        try:
            (xml_key, xml_filename) = get_article_xml_key(bucket, expanded_folder_name)
    
            # Rename the XML file to match what is used already
            new_key_name = self.outbox_new_key_name(
                prefix=self.crossref_outbox_folder,
                xml_filename=xml_filename)

            self.copy_article_xml_to_crossref_outbox(
                new_key_name=new_key_name,
                source_bucket_name=self.expanded_bucket_name,
                old_key_name=xml_key.name)

            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Crossref",
                                    "end", "Finished scheduling of crossref deposit " + article_id +
                                    " for version " + version + " run " + str(run))

        except Exception as exception:
            self.logger.exception("Exception when scheduling crossref")
            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Crossref",
                                    "error", "Error scheduling crossref " + article_id +
                                    " message:" + str(exception))
            return False

        return True


    def outbox_new_key_name(self, prefix, xml_filename):
        "key name for where on S3 to place the XML file"
        try:
            return prefix + xml_filename
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
