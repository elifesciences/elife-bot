from testfixtures import TempDirectory
import test_activity_data as data


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







