import os
import shutil
from collections import OrderedDict
import requests
from provider import utils
from provider.article_processing import file_extension


INF_FILE_NAME_ID_FORMAT = "inf%s"

INF_FILE_NAME_FORMAT = "elife-%s-%s.%s"

REQUESTS_TIMEOUT = 10


def download_file(from_path, to_file, user_agent=None):
    "download file to disk"
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    request = requests.get(from_path, timeout=REQUESTS_TIMEOUT, headers=headers)
    if request.status_code == 200:
        with open(to_file, "wb") as open_file:
            open_file.write(request.content)
        return to_file
    raise RuntimeError(
        "GET request returned a %s status code for %s"
        % (request.status_code, from_path)
    )


def download_images(href_list, to_dir, activity_name, logger, user_agent=None):
    "download images from imgur"
    href_to_file_name_map = OrderedDict()
    for href in href_list:
        file_name = href.rsplit("/", 1)[-1]
        to_file = os.path.join(to_dir, file_name)
        # todo!!! improve handling of potentially duplicate file_name values
        if href in href_to_file_name_map.keys():
            logger.info("%s, href %s was already downloaded" % (activity_name, href))
            continue
        try:
            file_path = download_file(href, to_file, user_agent)
        except RuntimeError as exception:
            logger.info(str(exception))
            logger.info("%s, href %s could not be downloaded" % (activity_name, href))
            continue
        logger.info("%s, downloaded href %s to %s" % (activity_name, href, to_file))
        # keep track of a map of href value to local file_name
        href_to_file_name_map[href] = file_path
    return href_to_file_name_map


def generate_new_image_file_names(
    href_to_file_name_map,
    article_id,
    identifier,
    caller_name,
    logger,
):
    "generate new file names for inline figure files"
    file_name_count = 1
    file_details_list = []
    for href, file_name in href_to_file_name_map.items():
        file_name_id = INF_FILE_NAME_ID_FORMAT % file_name_count
        new_file_name = INF_FILE_NAME_FORMAT % (
            utils.pad_msid(article_id),
            file_name_id,
            file_extension(file_name),
        )
        logger.info(
            "%s, for %s, file name %s changed to file name %s"
            % (caller_name, identifier, file_name, new_file_name)
        )

        # add the file details for using later to add XML file tags
        file_details = {
            "from_href": href,
            "file_name": file_name,
            "file_type": "figure",
            "upload_file_nm": new_file_name,
            "id": file_name_id,
        }
        file_details_list.append(file_details)

        # increment the file name counter
        file_name_count += 1
    return file_details_list


def generate_new_image_file_paths(
    file_details_list,
    content_subfolder,
    identifier,
    caller_name,
    logger,
):
    "generate new file path for new file names"
    for detail in file_details_list:
        new_file_asset = os.path.join(content_subfolder, detail.get("upload_file_nm"))
        detail["href"] = new_file_asset
        logger.info(
            "%s, for %s, file %s new asset value %s"
            % (caller_name, identifier, detail.get("upload_file_nm"), new_file_asset)
        )
    return file_details_list


def modify_href_to_file_name_map(href_to_file_name_map, file_details_list):
    "generate new XML href to file name map from file details list"
    for detail in file_details_list:
        href_to_file_name_map[detail.get("from_href")] = detail.get("upload_file_nm")
    return href_to_file_name_map


def move_images(file_details_list, to_dir, identifier, caller_name, logger):
    "move images from old to new file path"
    image_asset_file_name_map = {}
    for detail in file_details_list:
        new_file_path = os.path.join(to_dir, detail.get("href"))
        logger.info(
            "%s, for %s, moving %s to %s"
            % (caller_name, identifier, detail.get("file_name"), new_file_path)
        )
        # move the file on disk
        shutil.move(detail.get("file_name"), new_file_path)
        # add the file path to the asset map
        image_asset_file_name_map[detail.get("href")] = new_file_path
    return image_asset_file_name_map
