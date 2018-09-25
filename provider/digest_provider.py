"functions shared by digest related activities"
from pprint import pformat
import os
import traceback
import requests
import log
from docx.opc.exceptions import PackageNotFoundError
from digestparser import build, conf
import provider.utils as utils
from provider.storage_provider import storage_context
import provider.lax_provider as lax_provider


IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("digest_provider.log", 'INFO', IDENTITY)


class ErrorCallingDigestException(Exception):
    pass


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


def docx_file_name(article_id):
    "file name for the digest docx file"
    return new_file_name(".docx", article_id)


def digest_resource_origin(storage_provider, filename, bucket_name, bucket_folder):
    "concatenate the origin of a digest file for the storage provider"
    if not filename or not bucket_name or bucket_folder is None:
        return None
    storage_provider_prefix = storage_provider + "://"
    orig_resource = storage_provider_prefix + bucket_name + "/" + bucket_folder
    return orig_resource + '/' + filename


def outbox_resource_path(storage_provider, msid, bucket_name):
    "the digest outbox bucket folder as a resource"
    article_id = utils.pad_msid(msid)
    storage_provider_prefix = storage_provider + "://"
    return storage_provider_prefix + bucket_name + "/digests/outbox/" + article_id


def outbox_dest_resource_path(storage_provider, digest, bucket_name):
    "the bucket folder where files will be saved"
    msid = utils.msid_from_doi(digest.doi)
    return outbox_resource_path(storage_provider, msid, bucket_name)


def outbox_file_dest_resource(storage_provider, digest, bucket_name, file_path):
    "concatenate the S3 bucket object path we copy the file to"
    resource_path = outbox_dest_resource_path(storage_provider, digest, bucket_name)
    file_name = file_path.split(os.sep)[-1]
    dest_file_name = new_file_name(
        msid=utils.msid_from_doi(digest.doi),
        file_name=file_name)
    dest_resource = resource_path + "/" + dest_file_name
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


def digest_get_request(url, verify_ssl, digest_id):
    "common get request logic to digests API"
    response = requests.get(url, verify=verify_ssl)
    LOGGER.info("Request to digest API: GET %s", url)
    LOGGER.info("Response from digest API: %s\n%s", response.status_code, response.content)
    status_code = response.status_code
    if status_code not in [200, 404]:
        raise ErrorCallingDigestException(
            "Error looking up digest " + digest_id + " in digest API: %s\n%s" %
            (status_code, response.content))

    if status_code == 200:
        return response.json()


def get_digest(digest_id, settings):
    "get digest from the endpoint"
    url = settings.digest_endpoint.replace('{digest_id}', str(digest_id))
    return digest_get_request(url, settings.verify_ssl, digest_id)


def digest_auth_key(settings, auth=False):
    "value for the Authorization header for digest API"
    if auth:
        return settings.digest_auth_key


def digest_auth_header(auth_key):
    "headers for edit and view unpublished content on the digest API"
    if auth_key:
        return {'Authorization': auth_key}
    return {}


def digest_content_type_header():
    "headers for describing the digest body"
    return {'Content-Type': 'application/vnd.elife.digest+json; version=1'}


def digest_put_request(url, verify_ssl, digest_id, data, auth_key=None):
    "put request logic to digests API"
    headers = digest_auth_header(auth_key)
    headers.update(digest_content_type_header())
    response = requests.put(url, json=data, verify=verify_ssl,
                            headers=headers)
    LOGGER.info("Put to digest API: PUT %s\n%s", url, pformat(data))
    LOGGER.info("Response from digest API: %s\n%s", response.status_code, response.content)
    status_code = response.status_code
    if not 300 > status_code >= 200:
        raise ErrorCallingDigestException(
            "Error put digest " + digest_id + " to digest API: %s\n%s" %
            (status_code, response.content))
    else:
        return response.content


def put_digest(digest_id, data, settings, auth=True):
    "put digest to the endpoint"
    url = settings.digest_endpoint.replace('{digest_id}', str(digest_id))
    return digest_put_request(url, settings.verify_ssl, digest_id, data,
                              digest_auth_key(settings, auth))


def approve_by_status(logger, article_id, status):
    "determine approval status by article status value"
    approve_status = None
    # PoA do not ingest digests
    if status == "poa":
        approve_status = False
        message = ("\nNot ingesting digest for PoA article {article_id}".format(
            article_id=article_id
        ))
        logger.info(message)
    return approve_status


def approve_by_run_type(settings, logger, article_id, run_type, version):
    "determine ingest approval based on the run_type and version"
    approve_status = None
    # VoR and is a silent correction, consult Lax for if it is not the highest version
    if run_type == "silent-correction":
        highest_version = lax_provider.article_highest_version(article_id, settings)
        try:
            if int(version) < int(highest_version):
                approve_status = False
                message = (
                    "\nNot ingesting digest for silent correction {article_id}" +
                    " version {version} is less than highest version {highest}").format(
                        article_id=article_id,
                        version=version,
                        highest=highest_version)
                logger.info(message)
        except TypeError as exception:
            approve_status = False
            message = (
                "\nException converting version to int for {article_id}, {exc}").format(
                    article_id=article_id,
                    exc=str(exception))
            logger.exception(message.lstrip())
    return approve_status


def approve_by_first_vor(settings, logger, article_id, version, status, auth=True):
    "check if it is not the first vor or not the highest version"
    approve_status = None
    first_vor = lax_provider.article_first_by_status(article_id, version, status, settings, auth)
    highest_version = lax_provider.article_highest_version(article_id, settings, auth)
    if not first_vor:
        approve_status = False
    elif first_vor and version and highest_version and int(version) < int(highest_version):
        approve_status = False
    return approve_status
