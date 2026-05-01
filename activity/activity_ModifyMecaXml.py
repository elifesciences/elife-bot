import os
import json
from xml.etree.ElementTree import Element
from elifetools import xmlio
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import bigquery, cleaner, preprint, utils
from activity.objects import MecaBaseActivity


class activity_ModifyMecaXml(MecaBaseActivity):
    "ModifyMecaXml activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ModifyMecaXml, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ModifyMecaXml"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Modify XML taken from a preprint MECA."

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
            insert_comments=True,
        )
        self.statuses["xml_root"] = True

        # modify the XML

        # 0. start by collecting values on which other logic depends
        # review date
        review_date_string = cleaner.review_date_from_docmap(
            docmap_string, identifier=version_doi
        )
        review_date_struct = None
        if review_date_string:
            # convert the review-date to a time_struct object
            review_date_struct = cleaner.date_struct_from_string(review_date_string)

        history_data = cleaner.docmap_preprint_history_from_docmap(docmap_string)

        # get copyright year
        copyright_year = cleaner.get_copyright_year(history_data, doi)

        # 1. remove old DOI, add DOI and version DOI
        article_id = cleaner.article_id_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )
        modify_article_id(xml_root, article_id, doi, version_doi)

        # 2. <article-categories> - remove old ones, add display channel, subject tags
        article_categories = cleaner.article_categories_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )
        # todo !!! add the display channel (waiting to confirm data source)
        cleaner.modify_article_categories(
            xml_root, display_channel=None, article_categories=article_categories
        )

        # 3. add or set volume tag
        volume = cleaner.volume_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )
        if not volume and copyright_year:
            # if not volume, calculate from the copyright year
            volume = utils.volume_from_year(copyright_year)
        cleaner.modify_volume(xml_root, volume)

        # 4. add or set elocation-id tag
        elocation_id = cleaner.elocation_id_from_docmap(
            docmap_string, version_doi=version_doi, identifier=version_doi
        )
        if not elocation_id:
            # elocation_id based on the DOI
            elocation_id = "RP%s" % utils.msid_from_doi(doi)
        modify_elocation_id(xml_root, elocation_id)

        # 5. remove <history> (if present), create <history> with a sent-for-review date
        modify_history(xml_root, review_date_struct, identifier=version_doi)

        # 6. add <pub-history>, with events and dates, including self-uri tags
        if history_data:
            # remove current version_doi data from history data
            history_data = cleaner.prune_history_data(history_data, doi, version)

            # if silent correction, remove pub-history if present
            if session.get_value("run_type") == "silent-correction":
                clear_pub_history(xml_root)

            try:
                xml_root = cleaner.add_pub_history_meca(
                    xml_root,
                    history_data,
                    docmap_string=docmap_string,
                    identifier=version_doi,
                    user_agent=getattr(self.settings, "user_agent", None),
                )
            except Exception as exception:
                self.logger.exception(
                    (
                        "%s, exception raised when adding pub-history"
                        " for article_id %s, version %s: %s"
                    )
                    % (self.name, article_id, version, str(exception))
                )
                self.end_cleaner_log(session)
                # Clean up disk
                self.clean_tmp_dir()
                return self.ACTIVITY_PERMANENT_FAILURE

        # 7. replace <permissions>, includes copyright statement, copyright holder, license type
        license_data_dict = cleaner.get_license_data(docmap_string, version_doi)
        copyright_holder = None
        if license_data_dict and license_data_dict.get("copyright"):
            copyright_holder = cleaner.get_copyright_holder(xml_file_path)
        cleaner.modify_permissions(
            xml_root, license_data_dict, copyright_year, copyright_holder
        )

        # 8. add Senior Editor and Reviewing Editor <contrib> tags
        editors = cleaner.editor_contributors(docmap_string, version_doi)
        article_meta_tag = xml_root.find(".//front/article-meta")
        if editors:
            # if silent correction, remove editor contrib-group if present
            if session.get_value("run_type") == "silent-correction":
                clear_editors(xml_root)

            cleaner.set_editors(article_meta_tag, editors)

        # 9. add data availability statement and data citations
        if session.get_value("run_type") != "silent-correction":
            data_availability_data = get_data_availability_data(
                article_id, version, self.settings, self.name, self.logger
            )
            if data_availability_data:
                try:
                    add_data_availability(xml_root, data_availability_data)
                except Exception as exception:
                    self.logger.exception(
                        (
                            "%s, exception raised when adding data availability data"
                            " for article_id %s, version %s: %s"
                        )
                        % (self.name, article_id, version, str(exception))
                    )
            else:
                self.logger.info(
                    "%s, no data availability data from BigQuery for article_id %s, version %s"
                    % (self.name, article_id, version)
                )

        # 10. add funding XML
        if session.get_value("run_type") != "silent-correction":
            funding_data = get_funding_data(
                article_id, version, self.settings, self.name, self.logger
            )
            if funding_data:
                try:
                    add_funding(xml_root, funding_data)
                except Exception as exception:
                    self.logger.exception(
                        (
                            "%s, exception raised when adding funding data"
                            " for article_id %s, version %s: %s"
                        )
                        % (self.name, article_id, version, str(exception))
                    )
            else:
                self.logger.info(
                    "%s, no funding data from BigQuery for article_id %s, version %s"
                    % (self.name, article_id, version)
                )

        # 11. add author ORCID details
        if session.get_value("run_type") != "silent-correction":
            author_data = get_author_data(
                article_id, version, self.settings, self.name, self.logger
            )
            if author_data:
                try:
                    add_author_orcid(xml_root, author_data, self.name, self.logger)
                except Exception as exception:
                    self.logger.exception(
                        (
                            "%s, exception raised when adding author ORCID data"
                            " for article_id %s, version %s: %s"
                        )
                        % (self.name, article_id, version, str(exception))
                    )
            else:
                self.logger.info(
                    "%s, no author data from BigQuery for article_id %s, version %s"
                    % (self.name, article_id, version)
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


def clear_article_id(xml_root):
    "remove article-id tags"
    article_meta_tag = xml_root.find(".//front/article-meta")
    if article_meta_tag:
        for article_id_tag in article_meta_tag.findall("article-id"):
            article_meta_tag.remove(article_id_tag)


def modify_article_id(xml_root, article_id, doi, version_doi):
    "modify the article-id tags"
    clear_article_id(xml_root)
    cleaner.set_article_id(xml_root, article_id, doi, version_doi)


def modify_elocation_id(xml_root, elocation_id):
    "modify elocation-id tag"
    if elocation_id:
        cleaner.set_elocation_id(xml_root, elocation_id)
    else:
        # remove elocation-id tag
        article_meta_tag = xml_root.find(".//front/article-meta")
        if article_meta_tag:
            for tag in article_meta_tag.findall("elocation-id"):
                article_meta_tag.remove(tag)


def modify_history(xml_root, review_date_struct, identifier):
    "modify history tag and add history dates"
    # remove history tags
    history_tag = xml_root.find(".//front/article-meta/history")
    if history_tag:
        for tag in history_tag.findall("*"):
            history_tag.remove(tag)
    # add the sent-for-review date to a history tag in the XML file
    if review_date_struct:
        cleaner.add_history_date(
            xml_root, "sent-for-review", review_date_struct, identifier
        )


def clear_pub_history(xml_root):
    "remove pub-history tags"
    for parent_tag in xml_root.findall(".//pub-history/.."):
        for pub_history_tag in parent_tag.findall("./pub-history"):
            parent_tag.remove(pub_history_tag)


def clear_editors(xml_root):
    "remove contrib-group tag containing editor contrib"
    contrib_types = ["editor", "senior_editor"]
    for contrib_type in contrib_types:
        for parent_tag in xml_root.findall(
            './/contrib-group/contrib[@contrib-type="%s"]/../..' % contrib_type
        ):
            for contrib_group_tag in parent_tag.findall(
                './contrib-group/contrib[@contrib-type="%s"]/..' % contrib_type
            ):
                parent_tag.remove(contrib_group_tag)


def add_data_availability(xml_root, data_availability_data):
    "parse data availability data and add to XML"
    data_availability_statement = None
    data_citations = []
    if data_availability_data:
        (
            data_availability_statement,
            data_citations,
        ) = bigquery.parse_data_availability_data(data_availability_data)
    if data_availability_statement:
        cleaner.set_data_availability(xml_root, data_availability_statement)
    if data_citations:
        dataset_list = cleaner.data_citation_dataset_list(data_citations)
        cleaner.set_data_citations(xml_root, dataset_list)


def get_data_availability_data(article_id, version, settings, caller_name, logger):
    "from BigQuery get the data availability data"
    bigquery_client = bigquery.get_client(settings, logger)
    try:
        return bigquery.get_data_availability_data(bigquery_client, article_id, version)
    except Exception as exception:
        logger.exception(
            (
                "%s, exception getting data availability data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (caller_name, article_id, version, str(exception))
        )
    return None


def get_funding_data(article_id, version, settings, caller_name, logger):
    "from BigQuery get the funding data"
    bigquery_client = bigquery.get_client(settings, logger)
    try:
        return bigquery.get_funding_data(bigquery_client, article_id, version)
    except Exception as exception:
        logger.exception(
            (
                "%s, exception getting funding data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (caller_name, article_id, version, str(exception))
        )
    return None


def add_funding(xml_root, funding_data):
    "adding funding XML using the funding_data"
    funding_awards = []
    if funding_data:
        funding_awards = bigquery.parse_funding_data(funding_data)
    if funding_awards:
        cleaner.set_funding_award_data(xml_root, funding_awards)


def get_author_data(article_id, version, settings, caller_name, logger):
    "from BigQuery get the author data"
    bigquery_client = bigquery.get_client(settings, logger)
    try:
        return bigquery.get_author_data(bigquery_client, article_id, version)
    except Exception as exception:
        logger.exception(
            (
                "%s, exception getting author data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (caller_name, article_id, version, str(exception))
        )
    return None


def tag_text(parent, tag_name, selector=None):
    "from the parent tag get the text of tag_name if present"
    if selector:
        tag = parent.find(".//%s%s" % (tag_name, selector))
    else:
        tag = parent.find(".//%s" % tag_name)
    if tag is not None:
        return tag.text
    return None


def author_detail_list_from_xml(xml_root):
    "from XML get a list of author contrib data for collating ORCID values"
    xml_author_list = []
    author_contrib_tags = xml_root.findall(
        './/article-meta//contrib[@contrib-type="author"]'
    )
    for contrib_tag in author_contrib_tags:
        xml_author = {}
        xml_author["last_name"] = tag_text(contrib_tag, "surname")
        xml_author["first_name"] = tag_text(contrib_tag, "given-names")
        xml_author["ORCID"] = tag_text(
            contrib_tag, "contrib-id", '[@contrib-id-type="orcid"]'
        )
        xml_author_list.append(xml_author)
    return xml_author_list


def author_token_value(last_name, first_name):
    "from author values compile a single token used for matching"
    if not first_name:
        return str(last_name)
    return "%s, %s" % (last_name, first_name[0])


def get_xml_author_transformations(xml_author_list, author_details):
    "compare author data and collect a list of XML modifications to make"
    # map XML author name token to non-empty ORCID values
    author_details_map = {}
    for author_detail in author_details:
        if not author_detail.get("ORCID"):
            continue
        author_token = author_token_value(
            author_detail.get("last_name"), author_detail.get("first_name")
        )
        author_details_map[author_token] = author_detail.get("ORCID")

    # collect a list of XML modifications
    xml_author_transformations = []
    for xml_author in xml_author_list:
        author_token = author_token_value(
            xml_author.get("last_name"), xml_author.get("first_name")
        )
        if author_token not in author_details_map.keys():
            continue
        # compare ORCID value
        if author_details_map.get(author_token):
            # check if ORCID value exists in XML
            if not xml_author.get("ORCID"):
                # add ORCID tag
                xml_author_transformations.append(
                    {
                        "action": "add",
                        "author_token": author_token,
                        "ORCID": author_details_map.get(author_token),
                    }
                )
            elif not xml_author.get("ORCID").endswith(
                author_details_map.get(author_token)
            ):
                # add additional ORCID tag
                xml_author_transformations.append(
                    {
                        "action": "add",
                        "author_token": author_token,
                        "ORCID": author_details_map.get(author_token),
                    }
                )
            else:
                # set authenticated attribute
                xml_author_transformations.append(
                    {
                        "action": "modify",
                        "author_token": author_token,
                        "ORCID": author_details_map.get(author_token),
                    }
                )
    return xml_author_transformations


def modify_author_xml(xml_root, author_transformations):
    "modify XML author contributor ORCID tags"
    author_transformations_map = {
        transformation.get("author_token"): transformation
        for transformation in author_transformations
    }

    for contrib_tag in xml_root.findall(".//contrib"):
        author_token = author_token_value(
            tag_text(contrib_tag, "surname"), tag_text(contrib_tag, "given-names")
        )
        if author_token not in author_transformations_map.keys():
            continue
        transformation = author_transformations_map.get(author_token)
        if transformation.get("action") == "add":
            # add ORCID tag
            orcid_tag = Element("contrib-id")
            orcid_tag.set("contrib-id-type", "orcid")
            orcid_tag.set("authenticated", "true")
            orcid_tag.text = "https://orcid.org/%s" % transformation.get("ORCID")
            orcid_tag.tail = "\n"
            contrib_tag.insert(0, orcid_tag)
        elif transformation.get("action") == "modify":
            # set authenticated attribute to existing ORCID tag
            orcid_tag = contrib_tag.find(".//contrib-id")
            orcid_tag.set("authenticated", "true")


def add_author_orcid(xml_root, author_data, caller_name, logger):
    "add author ORCID data to the XML"
    # parse author data from BigQuery
    author_details = None
    if author_data:
        author_details = bigquery.parse_author_data(author_data)
    if not author_details:
        logger.info("%s, parsed no author_details from author_data" % caller_name)
        return

    # parse author details from the XML
    xml_author_list = author_detail_list_from_xml(xml_root)
    logger.info("%s, found %s authors in the XML" % (caller_name, len(xml_author_list)))

    # match XML authors to author_details data to determine XML transformations
    xml_author_transformations = get_xml_author_transformations(
        xml_author_list, author_details
    )
    logger.info(
        "%s, collected xml_author_transformations: %s"
        % (caller_name, xml_author_transformations)
    )

    # modify the XML
    modify_author_xml(xml_root, xml_author_transformations)
    logger.info("%s, modified author XML" % (caller_name))
