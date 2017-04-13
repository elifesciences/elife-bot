from testfixtures import TempDirectory
import test_activity_data as data
from shutil import copyfile
from shutil import copy
import shutil
import re
import os


class FakeSession:

    def __init__(self, fake_session):
        #self.settings = settings
        #default test data
        self.session_dict = fake_session

    def store_value(self, execution_id, key, value):
        self.session_dict[key] = value

    def get_value(self, execution_id, key):
        try:
            return self.session_dict[key]
        except:
            return None

    @staticmethod
    def get_full_key(execution_id, key):
        return execution_id + '__' + key


class FakeS3Connection:

    def __init__(self):
        self.buckets_dict = {
            'origin_bucket': data.bucket_origin_file_name,
            'dest_bucket': data.bucket_dest_file_name
        }

    def get_bucket(self, mock_bucket_name):
        return self.buckets_dict[mock_bucket_name]





## PostEIFBridge Tests TODO: split in 2 files?

class FakeSQSMessage:
    def __init__(self, directory):
        self.dir = directory

    def set_body(self, body):
        self.dir.write("fake_sqs_body", body)


class FakeSQSConn:
    def __init__(self, directory):
        self.dir = directory

    def get_queue(self, queue):
        return FakeSQSQueue(self.dir) #self.get_object('FakeSQSQueue', self.dir)


class FakeSQSQueue:
    def __init__(self, directory):
        self.dir = directory

    # def write(self, body_dir):
    #     self.dir.write("fake_sqs_queue_container", body_dir.read("fake_sqs_body"))
    def write(self, message):
        self.dir.write("fake_sqs_queue_container", message.dir.read("fake_sqs_body"))

    def read(self, dir_name):
        return self.dir.read(dir_name)

class FakeStorageProviderConnection:
    def get_connection(self, aws_access_key_id, aws_secret_access_key):
        return None

    def get_resource(self, conn, name):
        if "elife-production-final" in name:
            return "tests\\files_source\\"
        else:
            return "tests\\files_dest\\"

class FakeStorageContext:

    def get_bucket_and_key(self, resource):
        p = re.compile(ur'(.*?)://(.*?)(/.*)')
        match = p.match(resource)
        protocol = match.group(1)
        bucket_name = match.group(2)
        s3_key = match.group(3)
        return bucket_name, s3_key

    def get_resource_to_file(self, resource, file):
        bucket_name, s3_key = self.get_bucket_and_key(resource)
        copyfile(data.ExpandArticle_files_source_folder + s3_key, file.name)

    def get_resource_as_string(self, origin):
        return '<mock><media content-type="glencoe play-in-place height-250 width-310" id="media1" mime-subtype="wmv" mimetype="video" xlink:href="elife-00569-media1.wmv"></media></mock>'

    def set_resource_from_filename(self, resource, file):
        #bucket_name, s3_key = self.get_bucket_and_key(resource)
        copy(file, data.ExpandArticle_files_dest_folder)

    def set_resource_from_string(self, resource, data, content_type=None):
        pass

    def list_resources(self, resource):
        return ["elife-00353-fig1-v1.tif", "elife-00353-v1", "elife-00353-v1.xml"]

    def copy_resource(self, origin, destination):
        pass

    # def set_contents_from_filename(self, storage_object, key, path):
    #     copyfile(file, "tests\\" + storage_object + key)

def fake_get_tmp_dir(path=None):
    tmp = 'tests/tmp/'
    directory = tmp
    if path is not None:
        directory = tmp + path
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def fake_clean_tmp_dir():
    tmp_dir = fake_get_tmp_dir()
    shutil.rmtree(tmp_dir)

class FakeResponse:
    def __init__(self, status_code, response_json):
        self.status_code = status_code
        self.response_json = response_json

    def json(self):
        return self.response_json

class FakeKey:

    def __init__(self, directory, destination=None, source=None, key=None):
        self.d = directory
        if destination is None:
            destination = data.bucket_origin_file_name
        if source is None:
            source = data.xml_content_for_xml_key

        if destination and source:
            self.d.write(destination, source)

        self.destination = destination
        if key:
            self.key = key

    def get_contents_as_string(self):
        return self.d.read(self.destination)

    def set_contents_from_string(self, json_output):
        self.d.write(self.destination, json_output)

    def check_file_contents(self, directory, file):
        return directory.read(file)

    def cleanup_fake_directories(self):
        self.d.cleanup()

class FakeFileInfo:
    def __init__(self):
        self.key = None

class FakeBucket:

    def get_key(self, key): #key will be u'00353.1/7d5fa403-cba9-486c-8273-3078a98a0b98/elife-00353-fig1-v1.tif' for example
        return key

class FakeLogger:
    def __init__(self):
        self.logdebug = "First logger debug"
        self.loginfo = "First logger info"
        self.logexception = "First logger exception"
        self.logerror = "First logger error"
    def debug(self, msg, *args, **kwargs):
        self.logdebug =  msg
    def info(self, msg, *args, **kwargs):
        self.loginfo = msg
    def exception(self, msg, *args, **kwargs):
        self.logexception = msg
    def error(self, msg, *args, **kwargs):
        self.logerror = msg







