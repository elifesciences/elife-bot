"functions shared by digest related activities"
import os
from S3utility.s3_notification_info import S3NotificationInfo
from provider.storage_provider import storage_context
import provider.utils as utils


def parse_data(data):
    "parse activity data from an S3 notification into useful bucket and file values"
    info = S3NotificationInfo.from_dict(data)
    filename = info.file_name[info.file_name.rfind('/')+1:]
    bucket_name = info.bucket_name
    bucket_folder = None
    if filename:
        bucket_folder = info.file_name.split(filename)[0]
    # replace + with spaces if present into a real_filename
    real_filename = utils.unquote_plus(filename)
    return real_filename, bucket_name, bucket_folder


def digest_resource_origin(storage_provider, filename, bucket_name, bucket_folder):
    "concatenate the origin of a digest file for the storage provider"
    if not filename or not bucket_name or bucket_folder is None:
        return None
    storage_provider_prefix = storage_provider + "://"
    orig_resource = storage_provider_prefix + bucket_name + "/" + bucket_folder
    return orig_resource + '/' + filename


def download_digest(storage, filename, resource_origin, to_dir):
    "download the digest filename from a bucket or storage to the to_dir"
    if not resource_origin:
        return None
    filename_plus_path = to_dir + os.sep + filename
    with open(filename_plus_path, 'wb') as open_file:
        storage.get_resource_to_file(resource_origin, open_file)
    return filename_plus_path


def download_digest_from_s3(settings, filename, bucket_name, bucket_folder, to_dir):
    "Connect to the S3 bucket and download the input"
    resource_origin = digest_resource_origin(
        storage_provider=settings.storage_provider,
        filename=filename,
        bucket_name=bucket_name,
        bucket_folder=bucket_folder
        )
    return download_digest(
        storage=storage_context(settings),
        filename=filename,
        resource_origin=resource_origin,
        to_dir=to_dir,
        )
