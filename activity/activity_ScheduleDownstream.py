import json
from collections import OrderedDict
from provider.storage_provider import storage_context
import provider.lax_provider as lax_provider
from activity.objects import Activity

"""
ScheduleDownstream.py activity
"""


class activity_ScheduleDownstream(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ScheduleDownstream, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "ScheduleDownstream"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Queue the article for depositing to PMC, pub router, and " +
                            "other recipients after an article is published.")
        self.logger = logger

    def do_activity(self, data=None):

        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        expanded_bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.expanded_bucket)

        publish_bucket_name = self.settings.poa_packaging_bucket

        article_id = data['article_id']
        version = data['version']
        run = data['run']
        expanded_folder_name = data['expanded_folder']
        status = data['status'].lower()
        run_type = data.get("run_type")

        self.emit_monitor_event(self.settings, article_id, version, run,
                                "Schedule Downstream", "start",
                                "Starting scheduling of downstream deposits for " + article_id)

        first_by_status = lax_provider.article_first_by_status(
            article_id, version, status, self.settings)

        try:
            xml_file_name = lax_provider.get_xml_file_name(
                self.settings, expanded_folder_name, expanded_bucket_name, version)
            xml_key_name = expanded_folder_name + "/" + xml_file_name
            outbox_list = choose_outboxes(status, outbox_map(), first_by_status, run_type)

            for outbox in outbox_list:
                self.rename_and_copy_to_outbox(
                    expanded_bucket_name, publish_bucket_name, xml_key_name, article_id, outbox)

            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Downstream",
                                    "end", "Finished scheduling of downstream deposits " +
                                    article_id + " for version " + version + " run " + str(run))

        except Exception as exception:
            self.logger.exception("Exception when scheduling downstream")
            self.emit_monitor_event(self.settings, article_id, version, run, "Schedule Downstream",
                                    "error", "Error scheduling downstream " + article_id +
                                    " message:" + str(exception))
            return False

        return True

    def rename_and_copy_to_outbox(self, source_bucket_name, dest_bucket_name,
                                  old_xml_key_name, article_id, prefix):
        """
        Invoke this for each outbox the XML is copied to
        Create a new XML file name and then copy from the old_xml_key_name to the new key name
        Prefix is an outbox path on S3 where the XML is copied to
        """
        # Rename the XML file to match what is used already
        new_key_name = new_outbox_xml_name(
            prefix=prefix,
            journal='elife',
            article_id=str(article_id).zfill(5))

        self.copy_article_xml_to_outbox(
            dest_bucket_name=dest_bucket_name,
            new_key_name=new_key_name,
            source_bucket_name=source_bucket_name,
            old_key_name=old_xml_key_name)

    def copy_article_xml_to_outbox(self, dest_bucket_name, new_key_name,
                                   source_bucket_name, old_key_name):
        "copy the XML file to an S3 outbox folder, for now"
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + source_bucket_name + "/" + old_key_name
        dest_resource = storage_provider + dest_bucket_name + "/" + new_key_name
        self.logger.info("ScheduleDownstream Copying %s to %s " % (orig_resource, dest_resource))
        storage.copy_resource(orig_resource, dest_resource)


def outbox_map():
    "map of outbox names to values"
    outboxes = OrderedDict()
    outboxes["pubmed"] = "pubmed/outbox/"
    outboxes["pmc"] = "pmc/outbox/"
    outboxes["publication_email"] = "publication_email/outbox/"
    outboxes["pub_router"] = "pub_router/outbox/"
    outboxes["cengage"] = "cengage/outbox/"
    outboxes["gooa"] = "gooa/outbox/"
    outboxes["wos"] = "wos/outbox/"
    outboxes["scopus"] = "scopus/outbox/"
    outboxes["cnpiec"] = "cnpiec/outbox/"
    outboxes["cnki"] = "cnki/outbox/"
    outboxes["clockss"] = "clockss/outbox/"
    return outboxes


def choose_outboxes(status, outbox_map, first_by_status, run_type=None):
    outbox_list = []

    if run_type != "silent-correction":
        if first_by_status:
            outbox_list.append(outbox_map.get("publication_email"))
        outbox_list.append(outbox_map.get("pubmed"))

    if status == "poa":
        pass

    elif status == "vor":
        outbox_list.append(outbox_map.get("pmc"))
        outbox_list.append(outbox_map.get("pub_router"))
        outbox_list.append(outbox_map.get("cengage"))
        outbox_list.append(outbox_map.get("gooa"))
        outbox_list.append(outbox_map.get("wos"))
        outbox_list.append(outbox_map.get("scopus"))
        outbox_list.append(outbox_map.get("cnpiec"))
        outbox_list.append(outbox_map.get("cnki"))
        outbox_list.append(outbox_map.get("clockss"))
    return outbox_list


def new_outbox_xml_name(prefix, journal, article_id):
    "New name we want e.g.: elife99999.xml"
    try:
        return prefix + journal + article_id + '.xml'
    except TypeError:
        return None
