from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError
from pydoc import locate
import json
import redis
from provider.utils import unicode_encode


def get_session(settings, input_data, session_key):
    settings_session_class = "RedisSession"  # Default
    if hasattr(settings, "session_class"):
        settings_session_class = settings.session_class

    session_class = locate("provider.execution_context." + settings_session_class)
    return session_class(settings, input_data, session_key)


class FileSession:

    # TODO : replace with better implementation - e.g. use Redis/Elasticache

    def __init__(self, settings, input_data, session_key):

        self.settings = settings
        self.input_data = input_data
        self.session_key = session_key

    def store_value(self, key, value):

        value = json.dumps(value)
        f = open(self.settings.workflow_context_path + self.get_full_key(key), "w")
        f.write(value)

    def get_value(self, key):

        value = None
        try:
            f = open(self.settings.workflow_context_path + self.get_full_key(key), "r")
            value = json.loads(f.readline())
        except:
            if self.input_data is not None and key in self.input_data:
                value = self.input_data[key]
        return value

    def get_full_key(self, key):

        return self.session_key + "__" + key


class RedisSession:
    def __init__(self, settings, input_data, session_key):

        self.input_data = input_data
        self.expire_key = settings.redis_expire_key
        self.session_key = session_key
        self.r = redis.StrictRedis(
            host=settings.redis_host, port=settings.redis_port, db=settings.redis_db
        )

    def store_value(self, key, value):

        value = json.dumps(value)
        self.r.hset(self.session_key, key, value)
        self.r.expire(self.session_key, self.expire_key)

    def get_value(self, key):

        value = self.r.hget(self.session_key, key)
        if value is None:
            if key in self.input_data:
                value = self.input_data[key]
        else:
            value = json.loads(value)
        return value


class S3Session:
    def __init__(self, settings, input_data, session_key):

        self.input_data = input_data
        self.conn = S3Connection(
            settings.aws_access_key_id, settings.aws_secret_access_key
        )
        self.bucket = self.conn.get_bucket(settings.s3_session_bucket)
        self.session_key = session_key

    def store_value(self, key, value):

        value = json.dumps(value)
        s3_key = Key(self.bucket)
        s3_key.key = self.get_full_key(key)
        s3_key.set_contents_from_string(str(value))

    def get_value(self, key):

        s3_key = Key(self.bucket)
        s3_key.key = self.get_full_key(key)
        value = None
        try:
            value = s3_key.get_contents_as_string()
            value = json.loads(unicode_encode(value))
        except S3ResponseError:
            if self.input_data is not None and key in self.input_data:
                value = self.input_data[key]
        return value

    def get_full_key(self, key):
        return self.session_key + "/" + key
