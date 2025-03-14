import os
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, meca
from activity.objects import MecaBaseActivity

# manifest article item tag id name format
ARTICLE_ID_PATTERN = "elife-{article_id}-v{version}"


class activity_ModifyMecaFiles(MecaBaseActivity):
    "ModifyMecaFiles activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ModifyMecaFiles, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ModifyMecaFiles"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Modify files in the expanded folder from a MECA"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "modify_manifest_xml": None,
            "modify_transfer_xml": None,
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
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        expanded_folder = session.get_value("expanded_folder")
        version_doi = session.get_value("version_doi")

        # local path to the article XML file
        xml_file_path = os.path.join(self.directories.get("TEMP_DIR"), article_xml_path)

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        self.logger.info(
            "%s, downloading manifest.xml for %s from %s"
            % (self.name, version_doi, resource_prefix)
        )
        (
            manifest_xml_file_path,
            manifest_storage_resource_origin,
        ) = self.download_manifest(storage, resource_prefix)

        # delete directives.xml file in the expanded folder
        self.logger.info(
            "%s, deleting directives.xml file for %s" % (self.name, version_doi)
        )
        self.delete_expanded_folder_files(
            asset_file_name_map={"directives.xml": "directives.xml"},
            resource_prefix=resource_prefix,
            file_name_list=["directives.xml"],
            storage=storage,
        )

        # remove mention of the directives.xml files from the manifest.xml
        clear_manifest_directives_item(manifest_xml_file_path, version_doi)

        # set id attribute for the article item tag in the manifest.xml
        id_value = ARTICLE_ID_PATTERN.format(article_id=article_id, version=version)
        self.logger.info(
            "%s, new MECA article id value %s for %s"
            % (self.name, id_value, version_doi)
        )
        modify_article_item_tag(manifest_xml_file_path, version_doi, id_value)
        self.statuses["modify_manifest_xml"] = True

        # update transfer.xml
        (
            transfer_xml_file_path,
            transfer_storage_resource_origin,
        ) = download_transfer_xml(
            storage,
            resource_prefix,
            self.directories.get("TEMP_DIR"),
            self.name,
            self.logger,
        )
        self.logger.info(
            "%s, modifying transfer.xml file for %s" % (self.name, version_doi)
        )
        with open(transfer_xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(meca.transfer_xml())
        self.statuses["modify_transfer_xml"] = True

        # upload manifest to the bucket
        self.logger.info(
            "%s, updating manifest XML to %s"
            % (self.name, manifest_storage_resource_origin)
        )
        storage.set_resource_from_filename(
            manifest_storage_resource_origin, manifest_xml_file_path
        )

        # upload manifest to the bucket
        self.logger.info(
            "%s, updating transfer XML to %s"
            % (self.name, transfer_storage_resource_origin)
        )
        storage.set_resource_from_filename(
            transfer_storage_resource_origin, transfer_xml_file_path
        )

        self.statuses["upload"] = True

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        self.end_cleaner_log(session)

        # Clean up disk
        self.clean_tmp_dir()

        return True


def clear_manifest_directives_item(xml_file_path, identifier):
    "remove item tag for directives file from manifest XML"
    root, doctype_dict, processing_instructions = cleaner.parse_manifest(xml_file_path)
    for item_tag in root.findall("{http://manuscriptexchange.org}item"):
        if (
            item_tag.find(
                '{http://manuscriptexchange.org}instance[@href="directives.xml"]'
            )
            is not None
        ):
            root.remove(item_tag)
    # write XML file to disk
    cleaner.write_manifest_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )


def modify_article_item_tag(xml_file_path, identifier, id_value):
    "modify the item tag of type article"
    root, doctype_dict, processing_instructions = cleaner.parse_manifest(xml_file_path)
    for item_tag in root.findall("{http://manuscriptexchange.org}item"):
        if item_tag.get("type") == "article":
            item_tag.set("id", id_value)
            break
    # write XML file to disk
    cleaner.write_manifest_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )


def download_transfer_xml(storage, resource_prefix, to_dir, caller_name, logger):
    "download transfer.xml from the bucket expanded folder"
    transfer_xml_file_path = os.path.join(to_dir, meca.TRANSFER_XML_PATH)
    transfer_storage_resource_origin = resource_prefix + "/" + meca.TRANSFER_XML_PATH
    logger.info(
        "%s, downloading %s to %s"
        % (caller_name, transfer_storage_resource_origin, transfer_xml_file_path)
    )
    with open(transfer_xml_file_path, "wb") as open_file:
        storage.get_resource_to_file(transfer_storage_resource_origin, open_file)
    return transfer_xml_file_path, transfer_storage_resource_origin
