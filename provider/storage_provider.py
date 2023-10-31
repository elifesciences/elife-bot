import os
import re
from io import BytesIO
import boto3
import botocore
import log


def storage_context(*args):
    return S3StorageContext(*args)


class S3StorageContext:
    def __init__(self, settings):

        self.context = {}
        self.settings = settings

    def get_client(self):
        reuse_s3_conn = os.environ.get('BOT_REUSE_S3_CONN', '0') == '1'
        if reuse_s3_conn:
            return self.settings.aws_conn('s3', {
                'aws_access_key_id': self.settings.aws_access_key_id,
                'aws_secret_access_key': self.settings.aws_secret_access_key,
            })

        return boto3.client(
            "s3",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
        )

    def get_client_from_cache(self):
        if "client" in self.context:
            client = self.context["client"]
        else:
            client = self.get_client()
            self.context["client"] = client
        return client

    # Resource format expected s3://my-bucket/my/path/abc.zip
    def s3_storage_objects(self, resource):
        pattern = re.compile(r"(.*?)://(.*?)(/.*)")
        match = pattern.match(resource)
        protocol = match.group(1)
        if protocol != "s3":
            # another implementation of this same 'interface'
            # could handle different resource types without
            # changing the external api
            raise UnsupportedResourceType()
        bucket_name = match.group(2)
        s3_key = match.group(3)
        return bucket_name, s3_key

    def resource_exists(self, resource):
        "check if an object exists in the bucket"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        if not s3_key:
            return None
        client = self.get_client_from_cache()
        try:
            client.head_object(Bucket=bucket_name, Key=s3_key.lstrip("/"))
        except botocore.exceptions.ClientError:
            # if response is 403 or 404, or the key does not exist
            return False
        return True

    def get_resource_as_string(self, resource):
        "return resource object as bytes"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        object_buffer = BytesIO()
        client = self.get_client_from_cache()
        client.download_fileobj(
            Bucket=bucket_name, Key=s3_key.lstrip("/"), Fileobj=object_buffer
        )
        return object_buffer.getvalue()

    def get_resource_to_file(self, resource, file):
        "save resource object data to file pointer"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        client = self.get_client_from_cache()
        client.download_fileobj(
            Bucket=bucket_name, Key=s3_key.lstrip("/"), Fileobj=file
        )

    def get_resource_attributes(self, resource):
        "return dict of object attributes"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        client = self.get_client_from_cache()
        return client.head_object(Bucket=bucket_name, Key=s3_key.lstrip("/"))

    def set_resource_from_filename(self, resource, file, metadata=None):
        "create object from file data, metadata can include ContentType key"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        kwargs = {
            "Filename": file,
            "Bucket": bucket_name,
            "Key": s3_key.lstrip("/"),
        }
        if metadata:
            kwargs["ExtraArgs"] = metadata
        client = self.get_client_from_cache()
        client.upload_file(**kwargs)

    def set_resource_from_string(self, resource, data, content_type=None):
        "create object and save data there"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        client = self.get_client_from_cache()
        kwargs = {
            "Body": data,
            "Bucket": bucket_name,
            "Key": s3_key.lstrip("/"),
        }
        if content_type:
            kwargs["ContentType"] = content_type
        client.put_object(**kwargs)
        # todo!!! optionally compare response etag to string MD5 to confirm it copied entirely

    def list_resources(self, folder, return_keys=False):
        "list all bucket objects for the folder"
        bucket_name, s3_key = self.s3_storage_objects(folder)
        folder = s3_key[1:] if s3_key[:1] == "/" else s3_key
        max_keys = 1000
        bucket_contents = []

        client = self.get_client_from_cache()
        # set IsTruncated in a pre-response prior to the while loop
        response = {"IsTruncated": True}
        while response.get("IsTruncated") is True:
            kwargs = {
                "Bucket": bucket_name,
                "MaxKeys": max_keys,
            }
            if folder:
                kwargs["Prefix"] = folder
            # handle the continuation token
            if response.get("NextContinuationToken"):
                kwargs["ContinuationToken"] = response.get("NextContinuationToken")
            elif response.get("ContinuationToken"):
                del kwargs["ContinuationToken"]
            # get max list of objects from the client
            response = client.list_objects_v2(**kwargs)
            if response.get("Contents"):
                # add the Contents list to the full list of objects
                bucket_contents += response.get("Contents")
        if return_keys:
            # return a dict of object data
            return bucket_contents
        # by default return a list of key names only
        return [key_dict.get("Key") for key_dict in bucket_contents]

    def copy_resource(
        self, orig_resource, dest_resource, additional_dict_metadata=None
    ):
        orig_bucket_name, orig_s3_key = self.s3_storage_objects(orig_resource)
        dest_bucket_name, dest_s3_key = self.s3_storage_objects(dest_resource)
        client = self.get_client_from_cache()

        copy_source = {
            "Bucket": orig_bucket_name,
            "Key": orig_s3_key.lstrip("/"),
        }

        kwargs = {
            "CopySource": copy_source,
            "Bucket": dest_bucket_name,
            "Key": dest_s3_key.lstrip("/"),
        }

        if additional_dict_metadata is not None:
            kwargs["MetadataDirective"] = "REPLACE"
            if additional_dict_metadata.get("Content-Type"):
                kwargs["ContentType"] = additional_dict_metadata.get("Content-Type")
            if additional_dict_metadata.get("Content-Disposition"):
                kwargs["ContentDisposition"] = additional_dict_metadata.get(
                    "Content-Disposition"
                )

        client.copy_object(**kwargs)

    def delete_resource(self, resource):
        bucket_name, s3_key = self.s3_storage_objects(resource)
        client = self.get_client_from_cache()
        client.delete_object(Bucket=bucket_name, Key=s3_key.lstrip("/"))


class UnsupportedResourceType(Exception):  # TODO
    pass
