from testfixtures import TempDirectory
import tests.activity.test_activity_data as data
from shutil import copyfile, copyfileobj
from shutil import copy
import shutil
import re
import os
from mock import MagicMock


class FakeSession:

    def __init__(self, fake_session):
        #self.settings = settings
        #default test data
        self.session_dict = fake_session

    def store_value(self, key, value):
        self.session_dict[key] = value

    def get_value(self, key):
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

    def lookup(self, mock_bucket_name):
        return self.get_bucket(mock_bucket_name)


class FakeSQSMessage:
    def __init__(self, directory):
        self.dir = directory

    def set_body(self, body):
        # write bytes
        self.dir.write("fake_sqs_body", bytes(body, 'utf-8'))

    def get_body(self):
        return self.dir.read("fake_sqs_body")

    def delete(self):
        pass


class FakeSQSConn:
    def __init__(self, directory):
        self.dir = directory

    def get_queue(self, queue):
        return FakeSQSQueue(self.dir) #self.get_object('FakeSQSQueue', self.dir)


class FakeSQSQueue:
    def __init__(self, directory, messages=None):
        self.dir = directory
        self.messages = []
        if messages:
            self.messages = messages

    # def write(self, body_dir):
    #     self.dir.write("fake_sqs_queue_container", body_dir.read("fake_sqs_body"))
    def write(self, message):
        self.dir.write("fake_sqs_queue_container", message.dir.read("fake_sqs_body"))

    def read(self, dir_name):
        return self.dir.read(dir_name)

    def get_messages(self, num_messages=1):
        "for mocking return a list of messages"
        return self.messages

    def delete_message(self, message):
        self.messages = [q_message for q_message in self.messages if message != q_message]


class FakeFTP:
    def __init__(self, ftp_instance=None):
        self.ftp_instance = ftp_instance

    def ftp_connect(self, **kwargs):
        return self.ftp_instance

    def ftp_to_endpoint(self, **kwargs):
        pass

    def ftp_disconnect(self, ftp_instance=None):
        pass


class FakeStorageProviderConnection:
    def get_connection(self, aws_access_key_id, aws_secret_access_key):
        return None

    def get_resource(self, conn, name):
        if "elife-production-final" in name:
            return "tests\\files_source\\"
        else:
            return "tests\\files_dest\\"

class FakeStorageContext:

    def __init__(self, directory=data.ExpandArticle_files_source_folder):
        "can instantiate specifying a data directory or use the default"
        self.dir = directory
        self.resources = ["elife-00353-fig1-v1.tif", "elife-00353-v1.pdf", "elife-00353-v1.xml"]

    def get_bucket_and_key(self, resource):
        p = re.compile(r'(.*?)://(.*?)(/.*)')
        match = p.match(resource)
        protocol = match.group(1)
        bucket_name = match.group(2)
        s3_key = match.group(3)
        return bucket_name, s3_key

    def get_resource_as_key(self, resource):
        bucket, s3_key = self.get_bucket_and_key(resource)
        attributes = {
            'last_modified': '2021-01-01T00:00:01.000Z'
        }
        return FakeKey(None, s3_key, **attributes)

    def resource_exists(self, resource):
        "check if a key exists"
        bucket, s3_key = self.get_bucket_and_key(resource)
        src = self.dir + s3_key
        return os.path.exists(src)

    def get_resource_to_file(self, resource, filelike):
        bucket_name, s3_key = self.get_bucket_and_key(resource)
        src = self.dir + s3_key
        with open(src, 'rb') as fsrc:
            filelike.write(fsrc.read())

    def get_resource_as_string(self, origin):
        return '<mock><media content-type="glencoe play-in-place height-250 width-310" id="media1" mime-subtype="wmv" mimetype="video" xlink:href="elife-00569-media1.wmv"></media></mock>'

    def set_resource_from_filename(self, resource, file_name):
        "resource name can be different than the file name"
        to_file_name = resource.split('/')[-1]
        dest = data.ExpandArticle_files_dest_folder + '/' + to_file_name
        copy(file_name, dest)

    def set_resource_from_string(self, resource, data, content_type=None):
        file_name = os.path.join(self.dir, resource.split('/')[-1])
        with open(file_name, 'wb') as open_file:
            open_file.write(data)

    def list_resources(self, resource):
        return self.resources

    def copy_resource(self, origin, destination, additional_dict_metadata=None):
        pass

    def delete_resource(self, resource):
        # delete from the destination folder
        file_name = data.ExpandArticle_files_dest_folder + '/' + resource.split('/')[-1]
        if os.path.exists(file_name):
            os.remove(file_name)

    def get_resource_to_file_pointer(self, resource, file_path):
        return None

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


class FakeRequest:
    def __init__(self):
        self.headers = {}
        self.body = None


class FakeResponse:
    def __init__(self, status_code, response_json=None, text=""):
        self.status_code = status_code
        self.response_json = response_json
        self.content = None
        self.text = text
        self.request = FakeRequest()
        self.headers = {}

    def json(self):
        return self.response_json


class FakeKey:

    def __init__(self, directory=None, destination=None, source=None, **kwargs):
        self.d = directory
        if destination is None:
            destination = data.bucket_origin_file_name
        if source is None:
            source = data.xml_content_for_xml_key

        if directory and destination and source:
            self.d.write(destination, source)

        self.destination = destination

        # set object attributes from remaining keyword arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_contents_as_string(self):
        return self.d.read(self.destination)

    def set_contents_from_string(self, json_output):
        self.d.write(self.destination, json_output)

    def set_contents_from_filename(self, filename, replace=None):
        file_destination = str(self.destination) + filename.split('/')[-1]
        with open(filename, 'rb') as fp:
            self.d.write(file_destination, fp.read())

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

    def list(self, prefix='', delimiter='', headers=''):
        "stub for mocking"
        pass


class FakeLogger:
    def __init__(self):
        self.logdebug = "First logger debug"
        self.loginfo = ["First logger info"]
        self.logexception = "First logger exception"
        self.logerror = "First logger error"

    def debug(self, msg, *args, **kwargs):
        self.logdebug = msg

    def info(self, msg, *args, **kwargs):
        # perform string replace on the message
        if args:
            try:
                rendered_msg = msg % args
            except TypeError:
                # if args were supplied as a tuple
                rendered_msg = msg % args[0]
        else:
            rendered_msg = str(msg)
        # append message to the log
        self.loginfo.append(rendered_msg)

    def warning(self, msg, *args, **kwargs):
        self.logwarning = msg

    def exception(self, msg, *args, **kwargs):
        self.logexception = msg

    def error(self, msg, *args, **kwargs):
        self.logerror = msg

    def addHandler(self, handler):
        pass

    def setLevel(self, level):
        pass


FakeLaxProvider = MagicMock()
FakeLaxProvider.get_xml_file_name = MagicMock(return_value='fake.xml')



