import os
import re
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import log


def StorageContext(*args):
    logger = log.logger("deprecated.log", "INFO", __name__, loggerName=__name__)
    logger.warning("provider.storage_provider.StorageContext() is deprecated")
    return S3StorageContext(args[0])


def storage_context(*args):
    return S3StorageContext(*args)


class S3StorageContext:
    def __init__(self, settings):

        self.context = {}
        self.context["buckets"] = {}
        self.settings = settings

    # Resource format expected s3://my-bucket/my/path/abc.zip
    def s3_storage_objects(self, resource):
        p = re.compile(r"(.*?)://(.*?)(/.*)")
        match = p.match(resource)
        protocol = match.group(1)
        if protocol != "s3":
            # another implementation of this same 'interface' could handle different resource types without
            # changing the external api
            raise UnsupportedResourceType()
        bucket_name = match.group(2)
        s3_key = match.group(3)
        bucket = self.get_bucket_from_cache(bucket_name)
        return bucket, s3_key

    def resource_exists(self, resource):
        "check if a key exists in the bucket"
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        return key.exists()

    def get_resource_as_key(self, resource):
        bucket, s3_key = self.s3_storage_objects(resource)
        return bucket.get_key(s3_key)

    def get_resource_to_file(self, resource, file):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        key.get_contents_to_file(file)

    def get_resource_as_string(self, resource):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        return key.get_contents_as_string()

    def set_resource_from_filename(self, resource, file):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        key.set_contents_from_filename(file)

    def set_resource_from_file(self, resource, file, metadata=None):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key

        if metadata is not None:
            for mdk in metadata:
                key.metadata[mdk] = metadata[mdk]

        key.set_contents_from_file(file)

    def set_resource_from_string(self, resource, data, content_type=None):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        if content_type != None:
            key.content_type = content_type

        key.set_contents_from_string(data)

    def get_resource_to_file_pointer(self, resource, file_path):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key

        fp = open(file_path, mode="wb")

        key.get_file(fp)
        fp.close()

        assert key.size == os.path.getsize(file_path), (
            "The file size of the local cached copy does not correspond to the original size on S3 of %s. "
            "This points to a corrupted download, check what's in %s"
            % (key.name, file_path)
        )
        fp = open(file_path, mode="rb")
        return fp

    def list_resources(self, folder):
        bucket, s3_key = self.s3_storage_objects(folder)
        folder = s3_key[1:] if s3_key[:1] == "/" else s3_key
        files = []
        if not folder:
            # get a list of all bucket contents if no folder is specified
            bucketlist = bucket.list()
            for key in bucketlist:
                files.append(key.name)
        else:
            # list files from the folder and its subfolders and return object names only
            bucketlist = bucket.list(prefix=folder + "/")
            for key in bucketlist:
                filename = key.name.rsplit("/", 1)[1]
                files.append(filename)

        return files

    def copy_resource(
        self, orig_resource, dest_resource, additional_dict_metadata=None
    ):
        orig_bucket, orig_s3_key = self.s3_storage_objects(orig_resource)

        if additional_dict_metadata is not None:
            metadata = {}
            for mdk in additional_dict_metadata:
                metadata[mdk] = additional_dict_metadata[mdk]
        else:
            metadata = None

        dest_bucket, dest_s3_key = self.s3_storage_objects(dest_resource)

        dest_key = dest_bucket.get_key(dest_s3_key, validate=True)
        if dest_key is None:
            dest_key = dest_bucket.new_key(dest_s3_key)
            dest_key.set_contents_from_string("")

        dest_bucket.copy_key(
            dest_key.name[1:], orig_bucket.name, orig_s3_key[1:], metadata=metadata
        )

    def delete_resource(self, resource):
        bucket, s3_key = self.s3_storage_objects(resource)
        bucket.delete_key(s3_key)

    def get_bucket_from_cache(self, bucket_name):

        if bucket_name in self.context["buckets"]:
            bucket = self.context["buckets"][bucket_name]
        else:
            bucket = self.get_bucket(bucket_name)
            self.context["buckets"][bucket_name] = bucket
        return bucket

    def get_bucket(self, bucket_name):

        conn = self.get_connection_from_cache()
        bucket = conn.get_bucket(bucket_name)
        return bucket

    def get_connection_from_cache(self):

        if "connection" in self.context:
            connection = self.context["connection"]
        else:
            connection = self.get_connection()
            self.context["connection"] = connection
        return connection

    def get_connection(self):

        conn = S3Connection(
            self.settings.aws_access_key_id, self.settings.aws_secret_access_key
        )
        return conn


class UnsupportedResourceType(Exception):  # TODO
    pass
