import json

import activity

from boto.s3.connection import S3Connection

from activity_ConvertJATS import activity_ConvertJATS as ConvertJATS

"""
ScheduleDownstream.py activity
"""

class activity_ScheduleDownstream(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ScheduleDownstream"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Queue the article for depositing to PMC, pub router, and " +
                            "other recipients after an article is published.")
        self.logger = logger

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket

        # Outbox folders on S3
        self.pubmed_outbox_folder = "pubmed/outbox/"
        self.pmc_outbox_folder  = "pmc/outbox/"
        self.publication_email_outbox_folder = "publication_email/outbox/"
        self.pub_router_outbox_folder = "pub_router/outbox/"
        self.cengage_outbox_folder = "cengage/outbox/"
        self.gooa_outbox_folder = "gooa/outbox/"
        self.wos_outbox_folder = "wos/outbox/"
        self.scopus_outbox_folder = "scopus/outbox/"

    def do_activity(self, data=None):

        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.expanded_bucket_name = (self.settings.publishing_buckets_prefix
                                     + self.settings.expanded_bucket)

        article_id = data['article_id']
        version = data['version']
        run = data['run']
        expanded_folder_name = data['expanded_folder']
        status = data['status'].lower()

        conn = S3Connection(self.settings.aws_access_key_id,
                            self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(self.expanded_bucket_name)

        self.emit_monitor_event(self.settings, article_id, version, run,
                                "Schedule Downstream", "start",
                                "Starting scheduling of downstream deposits for " + article_id)

        try:
            (xml_key, xml_filename) = ConvertJATS.get_article_xml_key(bucket, expanded_folder_name)

            outbox_list = self.choose_outboxes(status)

            for outbox in outbox_list:
                self.rename_and_copy_to_outbox(xml_key, article_id, outbox)

            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Downstream",
                                    "end", "Finished scheduling of downstream deposits " +
                                    article_id + " for version " + version + " run " + str(run))
        except Exception as e:
            self.logger.exception("Exception when scheduling downstream")
            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Downstream",
                                    "error", "Error scheduling downstream " + article_id +
                                    " message:" + e.message)
            return False

        return True


    def choose_outboxes(self, status):
        outbox_list = []

        if status == "poa":
            outbox_list.append(self.pubmed_outbox_folder)
            outbox_list.append(self.publication_email_outbox_folder)

        elif status == "vor":
            outbox_list.append(self.pubmed_outbox_folder)
            outbox_list.append(self.pmc_outbox_folder)
            outbox_list.append(self.publication_email_outbox_folder)
            outbox_list.append(self.pub_router_outbox_folder)
            outbox_list.append(self.cengage_outbox_folder)
            outbox_list.append(self.gooa_outbox_folder)
            outbox_list.append(self.wos_outbox_folder)
            outbox_list.append(self.scopus_outbox_folder)

        return outbox_list


    def rename_and_copy_to_outbox(self, old_xml_key, article_id, prefix):
        """
        Invoke this for each outbox the XML is copied to
        Create a new XML file name and then copy from the old_xml_key to the new key name
        Prefix is an outbox path on S3 where the XML is copied to
        """
        # Rename the XML file to match what is used already
        new_key_name = self.new_outbox_xml_name(
            prefix=prefix,
            journal='elife',
            article_id=str(article_id).zfill(5))

        self.copy_article_xml_to_outbox(
            new_key_name=new_key_name,
            source_bucket_name=self.expanded_bucket_name,
            old_key_name=old_xml_key.name)


    def new_outbox_xml_name(self, prefix, journal, article_id):
        """
        New name we want e.g.: elife99999.xml
        """
        try:
            return prefix + journal + article_id + '.xml'
        except TypeError:
            return None


    def copy_article_xml_to_outbox(self, new_key_name, source_bucket_name, old_key_name):
        """
        Used for uploading to the crossref outbox, for now
        """
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.publish_bucket)

        key = bucket.copy_key(new_key_name, source_bucket_name, old_key_name)



