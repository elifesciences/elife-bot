import os
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, meca, preprint, utils
from activity.objects import MecaBaseActivity

# manifest article item tag id name format
ARTICLE_ID_PATTERN = "elife-{article_id}-v{version}"

# folder name to use for subfolder in MECA file as a standard
MECA_SUB_FOLDER_NAME = "content"


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
        run_type = session.get_value("run_type")

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

        # download manifest.xml
        self.logger.info(
            "%s, downloading manifest.xml for %s from %s"
            % (self.name, version_doi, resource_prefix)
        )
        (
            manifest_xml_file_path,
            manifest_storage_resource_origin,
        ) = self.download_manifest(storage, resource_prefix)

        # rename MECA files if not a silent-correction and subfolder name can be changed
        if run_type != "silent-correction":
            # find subfolder name based on the location of the article XML file
            content_subfolder = meca.meca_content_folder(article_xml_path)
            self.logger.info(
                "%s, content_subfolder name found for %s: %s"
                % (self.name, version_doi, content_subfolder)
            )
            change_subfolder_name = bool(content_subfolder != MECA_SUB_FOLDER_NAME)

            file_paths = []
            if change_subfolder_name:
                file_paths = content_folder_paths(
                    storage, resource_prefix, expanded_folder, content_subfolder
                )
                self.logger.info("%s, file_paths to move: %s" % (self.name, file_paths))
            # generate new XML file name
            new_xml_file_name = preprint.PREPRINT_XML_FILE_NAME_PATTERN.format(
                article_id=utils.pad_msid(article_id), version=version
            )
            change_article_xml_file_name = bool(
                article_xml_path.rsplit("/", 1)[-1] != new_xml_file_name
            )

            # create a new article XML file path depending on the content folder name
            if change_subfolder_name:
                # new content subfolder name
                new_xml_file_path = "%s/%s" % (
                    MECA_SUB_FOLDER_NAME,
                    new_xml_file_name,
                )
            else:
                # use existing content subfolder name
                new_xml_file_path = "%s/%s" % (
                    content_subfolder,
                    new_xml_file_name,
                )

            file_transfer_map = {}
            if change_article_xml_file_name:
                self.logger.info(
                    "%s, will use a new article XML file path: %s"
                    % (self.name, new_xml_file_path)
                )

            if change_subfolder_name:
                file_transfer_map = content_folder_file_transfer_map(
                    file_paths,
                    content_subfolder,
                    article_xml_path,
                    new_xml_file_path,
                )
            elif change_article_xml_file_name:
                # only change the XML file name if not changing the subfolder name
                file_transfer_map = {article_xml_path: new_xml_file_path}

            self.logger.info(
                "%s, file_transfer_map: %s" % (self.name, file_transfer_map)
            )

            self.logger.info(
                "%s, moving files in the expanded folder to the new content folder for %s"
                % (self.name, version_doi)
            )
            modify_content_folder(
                storage,
                resource_prefix,
                file_transfer_map,
                content_subfolder,
            )

            self.logger.info(
                "%s, modifying manifest.xml with new content folder href values for %s"
                % (self.name, version_doi)
            )
            modify_content_folder_manifest_items(
                manifest_xml_file_path, file_transfer_map, identifier=version_doi
            )

            # change the article_xml_path value in the session
            session.store_value("article_xml_path", new_xml_file_path)

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


def content_folder_paths(storage, resource_prefix, expanded_folder, content_subfolder):
    "get a list of files in the content subfolder of the MECA bucket expanded folder"
    # find files to move from the bucket content folder
    content_subfolder_resource_prefix = "%s/%s/" % (
        resource_prefix,
        content_subfolder,
    )
    content_bucket_paths = storage.list_resources(content_subfolder_resource_prefix)
    content_subfolder_path = "%s/%s/" % (expanded_folder, content_subfolder)
    content_bucket_paths = [
        path for path in content_bucket_paths if path.startswith(content_subfolder_path)
    ]
    return sorted(
        [
            path.rsplit(expanded_folder, 1)[-1].lstrip("/")
            for path in content_bucket_paths
        ]
    )


def content_folder_file_transfer_map(
    file_paths, content_subfolder, old_xml_file_path, new_xml_file_path
):
    "generate map of old to new paths from the content folder of the MECA bucket expanded folder"
    # map of old to new file names
    file_transfer_map = {}
    for file_path in file_paths:
        file_transfer_map[file_path] = file_path.replace(
            "%s/" % content_subfolder, "%s/" % MECA_SUB_FOLDER_NAME.rstrip("/")
        )
    # rename the article XML file
    file_transfer_map[old_xml_file_path] = new_xml_file_path
    return file_transfer_map


def modify_content_folder(
    storage,
    resource_prefix,
    file_transfer_map,
    content_subfolder,
):
    "move content files in the MECA bucket expanded folder to the default folder name"
    # move the files in the bucket expanded folder
    old_folder_list = []
    for old_file_path, new_file_path in file_transfer_map.items():
        old_s3_resource = resource_prefix + "/" + old_file_path
        new_s3_resource = resource_prefix + "/" + new_file_path
        # copy old key to new key
        storage.copy_resource(old_s3_resource, new_s3_resource)
        # delete old key
        storage.delete_resource(old_s3_resource)
        # collect subfolder names from the old folder path
        folder_path = old_file_path.rsplit("/", 1)[0]
        if folder_path not in old_folder_list:
            old_folder_list.append(folder_path)
    # delete subfolder paths
    for folder_path in old_folder_list:
        storage.delete_resource(resource_prefix + "/" + folder_path)
    # finally delete the old content folder
    storage.delete_resource(resource_prefix + "/" + content_subfolder)


def modify_content_folder_manifest_items(
    manifest_xml_file_path, file_transfer_map, identifier
):
    "modify the item tag href values in the manifest.xml"
    # rename file paths in manifest.xml file
    (
        manifest_root,
        doctype_dict,
        processing_instructions,
    ) = cleaner.parse_manifest(manifest_xml_file_path)
    for item_tag in manifest_root.findall(".//{http://manuscriptexchange.org}item"):
        instance_tag = item_tag.find(".//{http://manuscriptexchange.org}instance")
        if instance_tag is not None:
            if instance_tag.get("href") in file_transfer_map:
                instance_tag.set(
                    "href", file_transfer_map.get(instance_tag.get("href"))
                )
    # write XML file to disk
    cleaner.write_manifest_xml_file(
        manifest_root,
        manifest_xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )
