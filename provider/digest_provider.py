"functions shared by digest related activities"
import os
import traceback
from docx.opc.exceptions import PackageNotFoundError
from digestparser import build, conf
import provider.utils as utils
from provider.storage_provider import storage_context


def build_digest(input_file, temp_dir, logger=None, digest_config=None):
    "Parse input and build a Digest object"
    if not input_file:
        return False, None
    try:
        digest = build.build_digest(input_file, temp_dir, digest_config)
    except PackageNotFoundError:
        # bad docx file
        if logger:
            logger.exception('exception in EmailDigest build_digest: %s' %
                             traceback.format_exc())
        return False, None
    return True, digest


def digest_config(config_section, config_file):
    "parse the config values from the digest config"
    return conf.parse_raw_config(conf.raw_config(config_section, config_file))


def new_file_name(file_name, msid):
    "new name for the files stored for internal use"
    if file_name and file_name.endswith('.docx'):
        return 'digest-{msid:0>5}.docx'.format(msid=msid)
    else:
        # current only one optional image will be in a package, rename it too
        extension = file_name.split('.')[-1]
        return 'digest-{msid:0>5}.{extension}'.format(msid=msid, extension=extension)


def digest_resource_origin(storage_provider, filename, bucket_name, bucket_folder):
    "concatenate the origin of a digest file for the storage provider"
    if not filename or not bucket_name or bucket_folder is None:
        return None
    storage_provider_prefix = storage_provider + "://"
    orig_resource = storage_provider_prefix + bucket_name + "/" + bucket_folder
    return orig_resource + '/' + filename


def outbox_dest_resource_path(storage_provider, digest, bucket_name):
    "the bucket folder where files will be saved"
    msid = utils.msid_from_doi(digest.doi)
    article_id = utils.pad_msid(msid)
    storage_provider = storage_provider + "://"
    return storage_provider + bucket_name + "/digests/outbox/" + article_id + "/"


def outbox_file_dest_resource(storage_provider, digest, bucket_name, file_path):
    "concatenate the S3 bucket object path we copy the file to"
    resource_path = outbox_dest_resource_path(storage_provider, digest, bucket_name)
    file_name = file_path.split(os.sep)[-1]
    dest_file_name = new_file_name(
        msid=utils.msid_from_doi(digest.doi),
        file_name=file_name)
    dest_resource = resource_path + dest_file_name
    return dest_resource


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


def has_image(digest_content):
    "check if the Digest object has an image file"
    if not digest_content.image:
        return False
    if not digest_content.image.file:
        return False
    return True
