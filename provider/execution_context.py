from pydoc import locate
import json
import redis
from provider.utils import unicode_encode
from provider.storage_provider import storage_context


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
            if self.input_data is not None and key in self.input_data:
                value = self.input_data[key]
        else:
            value = json.loads(value)
        return value


class S3Session:
    def __init__(self, settings, input_data, session_key):

        self.storage = storage_context(settings)
        self.storage_provider = settings.storage_provider + "://"
        self.bucket_name = settings.s3_session_bucket
        self.input_data = input_data
        self.session_key = session_key

    def store_value(self, key, value):

        value = json.dumps(value)
        full_key = self.get_full_key(key)
        s3_resource = self.get_s3_resource(full_key)
        self.storage.set_resource_from_string(s3_resource, str(value))

    def get_value(self, key):

        full_key = self.get_full_key(key)
        s3_resource = self.get_s3_resource(full_key)
        value = None
        try:
            value = self.storage.get_resource_as_string(s3_resource)
            value = json.loads(unicode_encode(value))
        except:
            if self.input_data is not None and key in self.input_data:
                value = self.input_data[key]
        return value

    def get_s3_resource(self, full_key):
        return self.storage_provider + self.bucket_name + "/" + full_key

    def get_full_key(self, key):
        return self.session_key + "/" + key
