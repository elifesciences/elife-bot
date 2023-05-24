import os
import json
import shutil
from xml.etree.ElementTree import ParseError, SubElement
from provider import cleaner
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import AcceptedBaseActivity


REPAIR_XML = False


class activity_AddCommentsToAcceptedSubmissionXml(AcceptedBaseActivity):
    "AddCommentsToAcceptedSubmissionXml activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AddCommentsToAcceptedSubmissionXml, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AddCommentsToAcceptedSubmissionXml"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Add production comments to the accepted submission XML."

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"add": None, "upload_xml": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        cleaner_log = session.get_value("cleaner_log")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # generate the production comments to see if there are any
        comments = cleaner.production_comments_for_xml(cleaner_log)
        if not comments:
            self.logger.info(
                "%s, %s production_comments is %s, activity returning True"
                % (self.name, input_filename, comments)
            )
            return True

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # read the XML
        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # parse XML
        try:
            root = cleaner.parse_article_xml(xml_file_path)
            self.logger.info("%s, %s XML root parsed" % (self.name, input_filename))
        except ParseError:
            log_message = "%s, XML ParseError exception parsing XML %s for file %s" % (
                self.name,
                xml_file_path,
                input_filename,
            )
            self.logger.exception(log_message)
            root = None
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        if root:
            try:
                # add to the XML in production-comments tag
                add_comments_to_xml(root, xml_file_path, comments, input_filename)
                self.statuses["add"] = True
            except:
                log_message = "%s, exception in add_comments_to_xml %s for file %s" % (
                    self.name,
                    xml_file_path,
                    input_filename,
                )
                self.logger.exception(log_message)

        # upload the modified XML file to the expanded folder
        if self.statuses.get("add"):
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True


def add_comments_to_xml(root, xml_file_path, comments, input_filename):
    "add each of the comments into a p tag inside a production-comments tag"
    article_meta_tag = root.find("./front/article-meta")
    # find or create the custom meta group tag
    custom_meta_group_tag = article_meta_tag.find("./custom-meta-group")
    if not custom_meta_group_tag:
        custom_meta_group_tag = SubElement(article_meta_tag, "custom-meta-group")
    # find or create the production comments tag
    production_comments_tag = article_meta_tag.find("./production-comments")
    if not production_comments_tag:
        production_comments_tag = SubElement(
            custom_meta_group_tag, "production-comments"
        )
    # add each comment to a new p tag
    for comment in comments:
        p_tag = SubElement(production_comments_tag, "p")
        p_tag.text = comment
    # write the modified XML to disk
    cleaner.write_xml_file(root, xml_file_path, input_filename)
