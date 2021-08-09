import json
import re
import time
from datetime import datetime
from elifetools import parseJATS as parser
from boto.s3.connection import S3Connection
from provider.execution_context import get_session
from provider.article_structure import ArticleInfo
from provider.article_structure import get_article_xml_key
from provider import utils
from activity.objects import Activity

"""
SendDashboardProperties.py activity
"""


class activity_SendDashboardProperties(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_SendDashboardProperties, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "SendDashboardProperties"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Send selected properites of article being processed to the dashboard"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """

        run = data['run']
        session = get_session(self.settings, data, run)
        version = session.get_value('version')
        article_id = session.get_value('article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, "Send dashboard properties", "start",
                                "Starting send of article properties to dashboard for article " + article_id)

        # first download the XML and parse it, a permanent failure if does not succeed
        try:
            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
            expanded_folder_name = session.get_value('expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix
                                      + self.settings.expanded_bucket)

            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(expanded_folder_bucket)

            bucket_folder_name = expanded_folder_name
            (xml_key, xml_filename) = get_article_xml_key(bucket, bucket_folder_name)
            if xml_key is None:
                error_message = "Article XML path not found"
                self.logger.error("%s for article_id %s" % (error_message, article_id))
                self.emit_monitor_event(
                    self.settings,
                    article_id,
                    version,
                    run,
                    "Send dashboard properties",
                    "error",
                    "Error in send of article properties to dashboard for article "
                    + article_id
                    + " message:"
                    + error_message,
                )
                return self.ACTIVITY_PERMANENT_FAILURE

            xml = xml_key.get_contents_as_string()
            soup = parser.parse_xml(xml)

            self.set_dashboard_properties(soup, article_id, version)

        except Exception as exception:
            self.logger.exception("Exception emitting dashboard properties")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Send dashboard properties", "error",
                                    "Error in send of article properties to dashboard for article  " + article_id +
                                    " message:" + str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        # next emit the monitor event, return False if not able to emit the message
        try:
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Send dashboard properties", "end",
                                    "Article properties sent to dashboard for article  " +
                                    article_id)

        except Exception as exception:
            self.logger.exception("Exception emitting dashboard properties")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Send dashboard properties", "error",
                                    "Error in send of article properties to dashboard for article  " + article_id +
                                    " message:" + str(exception))
            return False

        return True

    def set_dashboard_properties(self, soup, article_id, version):

        doi = parser.doi(soup)
        self.set_monitor_property(self.settings, article_id, "doi", doi,
                                  "text", version=version)

        title = utils.tidy_whitespace(parser.full_title(soup))
        self.set_monitor_property(self.settings, article_id, "title", title,
                                  "text", version=version)

        status = utils.article_status(parser.is_poa(soup))
        self.set_monitor_property(self.settings, article_id, "status", status,
                                  "text", version=version)

        pub_date = time.strftime(utils.PUB_DATE_FORMAT, parser.pub_date(soup))
        self.set_monitor_property(self.settings, article_id, "publication-date", pub_date,
                                  "text", version=version)

        article_type = parser.article_type(soup)
        self.set_monitor_property(self.settings, article_id, "article-type", article_type,
                                  "text", version=version)

        # TODO BELOW
        authors = []
        corresponding_authors = []
        contributors = parser.contributors(soup)
        for contributor in contributors:

            author = ""
            given_names = contributor.get("given-names")
            surname = contributor.get("surname")

            if surname and given_names:
                author = str.join(" ", (given_names, surname))

            elif surname:
                author = surname

            if "corresp" in contributor and contributor["corresp"] == 'yes':
                corresponding_authors.append(author)

            authors.append(author)

        corresponding_authors_text = str.join(", ", corresponding_authors)
        self.set_monitor_property(self.settings, article_id, "corresponding-authors",
                                  corresponding_authors_text,
                                  "text", version=version)

        authors_text = str.join(", ", authors)
        self.set_monitor_property(self.settings, article_id, "authors", authors_text,
                                  "text", version=version)
