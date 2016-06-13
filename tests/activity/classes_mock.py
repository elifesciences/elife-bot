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


class FakeKey:

    def __init__(self, directory, destination=None):
        self.d = directory
        #self.d.write(file_in_bucket, data.bucket[file_in_bucket])
        if destination == None:
            self.d.write(data.bucket_origin_file_name, data.xml_content_for_xml_key)

    def get_contents_as_string(self):
        return self.d.read(data.bucket_origin_file_name)
        #return data.bucket[self]

    def set_contents_from_string(self, json_output):
        #self.d.write(self, data.bucket[self])
        self.d.write(data.bucket_dest_file_name, json_output)
        #save in the mock directory

    def check_file_contents(self, directory, file):
        return directory.read(file)

    def cleanup_fake_directories(self):
        self.d.cleanup()


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


def fake_monitor(self, settings, item_identifier, name, value, property_type, version=0):
        settings = settings
        item_identifier = item_identifier
        name = name
        value = value
        property_type = property_type
        version = version

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

    def set_resource_from_file(self, resource, file):
        #bucket_name, s3_key = self.get_bucket_and_key(resource)
        copy(file, data.ExpandArticle_files_dest_folder)

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







