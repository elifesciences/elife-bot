import os
import json
from elifetools import xmlio
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, github_provider
from activity.objects import MecaBaseActivity


class activity_MecaPeerReviews(MecaBaseActivity):
    "MecaPeerReviews activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaPeerReviews, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaPeerReviews"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Download peer reviews and add them to MECA XML."

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "download": None,
            "docmap_string": None,
            "xml_root": None,
            "upload": None,
        }

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        article_xml_path = session.get_value("article_xml_path")
        expanded_folder = session.get_value("expanded_folder")
        version_doi = session.get_value("version_doi")

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # local path to the article XML file
        xml_file_path = os.path.join(
            self.directories.get("INPUT_DIR"), article_xml_path
        )

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        orig_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # download XML from the bucket folder
        storage_resource_origin = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        self.statuses["download"] = True

        # get docmap as a string
        docmap_string = session.get_value("docmap_string")
        self.statuses["docmap_string"] = True

        # get sub-article data from docmap
        self.logger.info(
            "%s, generating xml_root including sub-article tags for version_doi: %s"
            % (self.name, version_doi)
        )
        terms_yaml = getattr(self.settings, "assessment_terms_yaml", None)

        # add sub-article XML to the ElementTree
        try:
            xml_root = cleaner.add_sub_article_xml(
                docmap_string,
                xml_file_path,
                terms_yaml,
                version_doi=version_doi,
                generate_dois=False,
            )
        except Exception as exception:
            log_message = (
                "%s, exception raised in add_sub_article_xml() for version_doi %s"
                % (
                    self.name,
                    version_doi,
                )
            )
            self.logger.exception("%s: %s" % (log_message, str(exception)))
            # add as a Github issue comment
            issue_comment = "elife-bot workflow message:\n\n%s" % log_message
            github_provider.add_github_issue_comment(
                self.settings, self.logger, self.name, version_doi, issue_comment
            )
            self.end_cleaner_log(session)
            return True

        self.statuses["xml_root"] = True

        # get the XML doctype
        root, doctype_dict, processing_instructions = xmlio.parse(
            xml_file_path,
            return_doctype_dict=True,
            return_processing_instructions=True,
        )

        # remove ext-link tag if it wraps an inline-graphic tag
        cleaner.clean_inline_graphic_tags(xml_root)

        # make XML pretty
        cleaner.pretty_sub_article_xml(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(
            xml_root, xml_file_path, version_doi, doctype_dict, processing_instructions
        )

        # save the response content to S3
        s3_resource = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, updating transformed XML to %s" % (self.name, s3_resource)
        )
        storage.set_resource_from_filename(s3_resource, xml_file_path)
        self.statuses["upload"] = True

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        self.end_cleaner_log(session)

        # Clean up disk
        self.clean_tmp_dir()

        return True
