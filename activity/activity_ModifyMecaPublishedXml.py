import os
import json
import time
from xml.etree.ElementTree import Element
from elifetools import xmlio
from jatsgenerator import build
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, meca, preprint, utils
from activity.objects import MecaBaseActivity


class activity_ModifyMecaPublishedXml(MecaBaseActivity):
    "ModifyMecaPublishedXml activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ModifyMecaPublishedXml, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ModifyMecaPublishedXml"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Modify MECA XML after it is published, such as add publication dates"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"docmap_string": None, "xml_root": None, "upload": None}

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
        article_id = session.get_value("article_id")

        # doi data
        doi, version = utils.version_doi_parts(version_doi)

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

        # convert entities to unicode if present
        self.logger.info(
            "%s, converting entities to unicode in %s" % (self.name, xml_file_path)
        )
        preprint.repair_entities(xml_file_path, self.name, self.logger)

        # get docmap as a string
        docmap_string = session.get_value("docmap_string")
        self.statuses["docmap_string"] = True

        # parse the XML root and doctype
        xml_root, doctype_dict, processing_instructions = xmlio.parse(
            xml_file_path,
            return_doctype_dict=True,
            return_processing_instructions=True,
            insert_pis=True,
        )
        self.statuses["xml_root"] = True

        # modify the XML

        # article-categories - remove old ones, add display channel, subject tags
        article_categories = cleaner.article_categories_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )
        # todo !!! add the display channel (waiting to confirm data source)
        cleaner.modify_article_categories(
            xml_root, display_channel=None, article_categories=article_categories
        )

        # get history data including up to the current version
        history_data = cleaner.docmap_preprint_history_from_docmap(docmap_string)
        history_data = cleaner.prune_history_data(history_data, doi, int(version) + 1)

        # add pub-date tags for each publication date from the docmap
        modify_pub_date(xml_root, history_data, doi)

        # get copyright year
        copyright_year = cleaner.get_copyright_year(history_data, doi)

        # reset volume tag
        volume = cleaner.volume_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )

        if not volume and copyright_year:
            # if not volume, calculate from the copyright year
            volume = utils.volume_from_year(copyright_year)

        if volume:
            cleaner.modify_volume(xml_root, volume)

        # replace <permissions>, includes copyright statement, copyright holder, license type
        license_data_dict = cleaner.get_license_data(docmap_string, version_doi)
        copyright_holder = None
        if license_data_dict and license_data_dict.get("copyright"):
            copyright_holder = cleaner.get_copyright_holder(xml_file_path)
        cleaner.modify_permissions(
            xml_root, license_data_dict, copyright_year, copyright_holder
        )

        # generate path to the PDF file
        content_subfolder = meca.meca_content_folder(article_xml_path)
        new_pdf_href = preprint.generate_new_pdf_href(
            article_id, version, content_subfolder
        )
        self.logger.info(
            "%s, generated new PDF href value %s for %s"
            % (self.name, new_pdf_href, version_doi)
        )
        # add / update self-uri tag in the article XML
        preprint.set_pdf_self_uri_tag(
            xml_root, new_pdf_href.rsplit("/", 1)[-1], version_doi
        )

        # finally, improve whitespace
        cleaner.format_article_meta_xml(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(
            xml_root, xml_file_path, version_doi, doctype_dict, processing_instructions
        )

        # save the response content to S3
        s3_resource = orig_resource + "/" + article_xml_path
        self.logger.info("%s, updating modified XML to %s" % (self.name, s3_resource))
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


def clear_year_only_pub_date(xml_root):
    "remove pub-date tag if it has only a year tag"
    article_meta_tag = xml_root.find(".//front/article-meta")
    for pub_date_tag in article_meta_tag.findall("pub-date"):
        if pub_date_tag.find("day") is None and pub_date_tag.find("month") is None:
            article_meta_tag.remove(pub_date_tag)


def modify_pub_date(xml_root, history_data, doi):
    "modify the pub-date tags"

    pub_date_list = []

    # get new data from the history_data if not present
    for data in history_data:
        if (
            data.get("doi")
            and data.get("doi").startswith(doi)
            and data.get("published")
        ):
            published_date = cleaner.date_struct_from_string(data.get("published"))
            if not pub_date_list:
                date_type = "original-publication"
            else:
                date_type = "update"
            pub_date_list.append({"date_type": date_type, "date": published_date})

    # clear old pub-date tags
    clear_pub_date_tags(xml_root)

    # determine where to insert pub-date tags
    insert_index = 0
    article_meta_tag = xml_root.find(".//front/article-meta")
    for index, tag in enumerate(article_meta_tag.findall("*")):
        if tag.tag in ["volume", "elocation-id", "history"]:
            insert_index = index
            break

    # choose first and last date to add
    if len(pub_date_list) <= 2:
        add_pub_date_list = pub_date_list
    else:
        add_pub_date_list = [pub_date_list[0], pub_date_list[-1]]

    # insert pub-date tags
    for pub_date_data in reversed(add_pub_date_list):
        pub_date_tag = Element("pub-date")
        pub_date_tag.set("date-type", pub_date_data.get("date_type"))
        pub_date_tag.set(
            "iso-8601-date", time.strftime("%Y-%m-%d", pub_date_data.get("date"))
        )
        build.set_dmy(pub_date_tag, pub_date_data.get("date"))
        article_meta_tag.insert(insert_index, pub_date_tag)


def clear_pub_date_tags(xml_root):
    "remove pub-date tags in article-meta"
    article_meta_tag = xml_root.find(".//front/article-meta")
    if article_meta_tag:
        for pub_date_tag in article_meta_tag.findall("pub-date"):
            article_meta_tag.remove(pub_date_tag)
