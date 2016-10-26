from pydoc import locate
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
import re


class StorageContext(object):
    def __new__(cls, *args):
        return S3StorageContext(args[0])

class S3StorageContext:

    def __init__(self, settings):

        self.context = {}
        self.context['buckets'] = {}
        self.settings = settings


    #Resource format expected s3://my-bucket/my/path/abc.zip
    def s3_storage_objects(self, resource):
        p = re.compile(ur'(.*?)://(.*?)(/.*)')
        match = p.match(resource)
        protocol = match.group(1)
        if protocol != 's3':
            # another implementation of this same 'interface' could handle different resource types without
            # changing the external api
            raise UnsupportedResourceType()
        bucket_name = match.group(2)
        s3_key = match.group(3)
        bucket = self.get_bucket_from_cache(bucket_name)
        return bucket, s3_key

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

    def set_resource_from_file(self, resource, file):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        key.set_contents_from_filename(file)

    def set_resource_from_string(self, resource, data):
        bucket, s3_key = self.s3_storage_objects(resource)
        key = Key(bucket)
        key.key = s3_key
        key.set_contents_from_string(data)

    def get_bucket_from_cache(self, bucket_name):

        if bucket_name in self.context['buckets']:
            bucket =  self.context['buckets'][bucket_name]
        else:
            bucket = self.get_bucket(bucket_name)
            self.context['buckets'][bucket_name] = bucket
        return bucket

    def get_bucket(self, bucket_name):

        conn = self.get_connection_from_cache()
        bucket = conn.get_bucket(bucket_name)
        return bucket

    def get_connection_from_cache(self):

        if 'connection' in self.context:
            connection =  self.context['connection']
        else:
            connection = self.get_connection()
            self.context['connection'] = connection
        return connection

    def get_connection(self):

        conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        return conn

class UnsupportedResourceType(Exception): #TODO
    pass



