import os
from provider import article_processing
from provider.storage_provider import storage_context


def get_to_folder_name(folder_name, date_stamp):
    """
    From the date_stamp
    return the S3 folder name to save published files into
    """
    return folder_name + date_stamp + "/"


def get_outbox_s3_key_names(settings, bucket_name, outbox_folder):
    """get a list of .xml S3 key names from the outbox"""
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/" + outbox_folder.rstrip("/")
    s3_key_names = storage.list_resources(orig_resource)
    # add back the outbox_folder to the key names
    full_s3_key_names = [
        (outbox_folder.rstrip("/") + "/" + key_name) for key_name in s3_key_names
    ]
    # return only the .xml files
    return [key_name for key_name in full_s3_key_names if key_name.endswith(".xml")]


def download_files_from_s3_outbox(
    settings, bucket_name, outbox_s3_key_names, to_dir, logger
):
    """from the s3 outbox folder,  download the .xml files"""
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/"

    for name in outbox_s3_key_names:
        # Download objects from S3 and save to disk
        file_name = name.split("/")[-1]
        file_path = os.path.join(to_dir, file_name)
        storage_resource_origin = orig_resource + "/" + name
        try:
            with open(file_path, "wb") as open_file:
                logger.info(
                    "Downloading %s to %s" % (storage_resource_origin, file_path)
                )
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except IOError:
            logger.exception("Failed to download file %s.", name)
            return False
    return True


def clean_outbox(settings, bucket_name, outbox_folder, to_folder, published_file_names):
    """Clean out the S3 outbox folder"""

    # Concatenate the expected S3 outbox file names
    s3_key_names = []
    for name in published_file_names:
        filename = name.split(os.sep)[-1]
        s3_key_name = outbox_folder + filename
        s3_key_names.append(s3_key_name)

    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"

    for name in s3_key_names:
        # Do not delete the from_folder itself, if it is in the list
        if name == outbox_folder:
            continue
        filename = name.split("/")[-1]
        new_s3_key_name = to_folder + filename

        orig_resource = storage_provider + bucket_name + "/" + name
        dest_resource = storage_provider + bucket_name + "/" + new_s3_key_name

        # First copy
        storage.copy_resource(orig_resource, dest_resource)

        # Then delete the old key if successful
        storage.delete_resource(orig_resource)


def upload_files_to_s3_folder(settings, bucket_name, to_folder, file_names):
    """
    Upload multiple files to a folder in an S3 bucket
    """
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"

    for file_name in file_names:
        resource_dest = (
            storage_provider
            + bucket_name
            + "/"
            + to_folder
            + article_processing.file_name_from_name(file_name)
        )
        storage.set_resource_from_filename(resource_dest, file_name)
