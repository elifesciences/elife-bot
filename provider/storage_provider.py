
from boto.s3.key import Key
from boto.s3.connection import S3Connection

class StorageProviderConnection:

    def get_connection(self, aws_access_key_id, aws_secret_access_key):
        conn = S3Connection(aws_access_key_id, aws_secret_access_key)
        return conn

    def get_bucket(self, conn, name):
        bucket = conn.get_bucket(name)
        return bucket

class StorageProviderKey:

    def key(self, bucket):
        return Key(bucket)