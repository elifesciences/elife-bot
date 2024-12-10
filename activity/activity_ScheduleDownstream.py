import json
from elifetools import parseJATS as parser
from provider.storage_provider import storage_context
from provider import downstream, lax_provider, utils, yaml_provider
from activity.objects import Activity

"""
ScheduleDownstream.py activity
"""


class activity_ScheduleDownstream(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ScheduleDownstream, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ScheduleDownstream"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue the article for depositing to PMC, pub router, and "
            + "other recipients after an article is published."
        )
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info(
                "%s, data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
            )

        expanded_bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        )

        publish_bucket_name = self.settings.poa_packaging_bucket

        article_id = data["article_id"]
        version = data["version"]
        run = data["run"]
        expanded_folder_name = data["expanded_folder"]
        status = data["status"].lower()
        run_type = data.get("run_type")

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            "Schedule Downstream",
            "start",
            "Starting scheduling of downstream deposits for " + article_id,
        )

        first_by_status = lax_provider.article_first_by_status(
            article_id, version, status, self.settings
        )

        rules = yaml_provider.load_config(self.settings)

        try:
            xml_file_name = lax_provider.get_xml_file_name(
                self.settings, expanded_folder_name, expanded_bucket_name, version
            )
            xml_key_name = expanded_folder_name + "/" + xml_file_name
            self.logger.info("%s, xml_key_name: %s" % (self.name, xml_key_name))

            # profile the article for checking do_not_schedule rules
            article_profile_type = get_article_profile_type(
                self.settings, expanded_bucket_name, xml_key_name
            )
            self.logger.info(
                "%s, article_profile_type: %s" % (self.name, article_profile_type)
            )

            # load XML and collect assessment keywords
            assessment_keywords = get_assessment_keywords(
                self.settings, expanded_bucket_name, xml_key_name
            )

            outbox_list = downstream.choose_outboxes(
                status,
                first_by_status,
                rules,
                run_type,
                article_profile_type,
                assessment_keywords,
            )

            self.logger.info(
                "%s, adding %s to outboxes: %s" % (self.name, xml_key_name, outbox_list)
            )

            for outbox in outbox_list:
                self.rename_and_copy_to_outbox(
                    expanded_bucket_name,
                    publish_bucket_name,
                    xml_key_name,
                    article_id,
                    outbox,
                )

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                "Schedule Downstream",
                "end",
                "Finished scheduling of downstream deposits "
                + article_id
                + " for version "
                + version
                + " run "
                + str(run),
            )

        except Exception as exception:
            self.logger.exception("Exception when scheduling downstream")
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                "Schedule Downstream",
                "error",
                "Error scheduling downstream "
                + article_id
                + " message:"
                + str(exception),
            )
            return False

        return True

    def rename_and_copy_to_outbox(
        self, source_bucket_name, dest_bucket_name, old_xml_key_name, article_id, prefix
    ):
        """
        Invoke this for each outbox the XML is copied to
        Create a new XML file name and then copy from the old_xml_key_name to the new key name
        Prefix is an outbox path on S3 where the XML is copied to
        """
        # Rename the XML file to match what is used already
        new_key_name = new_outbox_xml_name(
            prefix=prefix, journal="elife", article_id=utils.pad_msid(article_id)
        )

        self.copy_article_xml_to_outbox(
            dest_bucket_name=dest_bucket_name,
            new_key_name=new_key_name,
            source_bucket_name=source_bucket_name,
            old_key_name=old_xml_key_name,
        )

    def copy_article_xml_to_outbox(
        self, dest_bucket_name, new_key_name, source_bucket_name, old_key_name
    ):
        "copy the XML file to an S3 outbox folder, for now"
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + source_bucket_name + "/" + old_key_name
        dest_resource = storage_provider + dest_bucket_name + "/" + new_key_name
        self.logger.info(
            "ScheduleDownstream Copying %s to %s " % (orig_resource, dest_resource)
        )
        storage.copy_resource(orig_resource, dest_resource)


def new_outbox_xml_name(prefix, journal, article_id):
    "New name we want e.g.: elife99999.xml"
    try:
        return prefix + journal + article_id + ".xml"
    except TypeError:
        return None


def get_article_profile_type(settings, expanded_bucket_name, xml_key_name):
    "return the profile type based on article_type and related article status"
    storage = storage_context(settings)
    s3_resource = (
        settings.storage_provider + "://" + expanded_bucket_name + "/" + xml_key_name
    )
    xml = storage.get_resource_as_string(s3_resource)

    soup = parser.parse_xml(xml)

    article_type = parser.article_type(soup)

    # return retraction_of_preprint if applicable
    if article_type != "retraction":
        return None
    # parse related articles
    related_articles = parser.related_article(soup)
    for related_article_data in related_articles:
        # check status of the related article
        msid = utils.msid_from_doi(related_article_data.get("xlink_href"))
        if msid:
            status_version_map = lax_provider.article_status_version_map(msid, settings)
            if len(status_version_map.keys()) <= 0:
                # if no vor or poa versions then assume it is preprint status
                return "retraction_of_preprint"
    return None


def get_assessment_keywords(settings, expanded_bucket_name, xml_key_name):
    "download artice XML and parse keywords in the assessment"
    assessment_keywords = []
    storage = storage_context(settings)
    s3_resource = (
        settings.storage_provider + "://" + expanded_bucket_name + "/" + xml_key_name
    )
    xml = storage.get_resource_as_string(s3_resource)

    soup = parser.parse_xml(xml)

    elife_assessment_json = parser.elife_assessment(soup)

    # collect keywords from the elife_assessment_json
    for keyword_group_types in ["significance", "strength"]:
        if elife_assessment_json.get(keyword_group_types):
            assessment_keywords += elife_assessment_json.get(keyword_group_types)

    return sorted(assessment_keywords)
