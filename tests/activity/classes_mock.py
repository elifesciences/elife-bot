from testfixtures import TempDirectory
import tests.activity.test_activity_data as data
from shutil import copyfile, copyfileobj
from shutil import copy
import shutil
import re
import os
from io import BytesIO
from datetime import datetime
from mock import MagicMock


class FakeSession:
    def __init__(self, fake_session):
        # self.settings = settings
        # default test data
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
        return execution_id + "__" + key


class FakeSQSClient:
    def __init__(self, directory=None, queues=None):
        self.dir = directory
        self.queues = {}
        if queues:
            self.queues = queues

    def get_queue_url(self, **kwargs):
        "for testing the QueueName and QueueUrl can be the same value"
        if (
            kwargs.get("QueueName")
            and kwargs.get("QueueName") not in self.queues.keys()
        ):
            self.queues[kwargs.get("QueueName")] = FakeSQSQueue(self.dir)
        return {"QueueUrl": kwargs.get("QueueName")}

    def receive_message(self, **kwargs):
        queue_url_response = self.get_queue_url(QueueName=kwargs.get("QueueUrl"))
        queue = self.queues.get(queue_url_response.get("QueueUrl"))
        if queue and queue.messages:
            return queue.messages[0]

    def send_message(self, **kwargs):
        # QueueUrl and MessageBody are accepted keyword arguments
        queue_url_response = self.get_queue_url(QueueName=kwargs.get("QueueUrl"))
        queue = self.queues.get(queue_url_response.get("QueueUrl"))
        if queue:
            queue.dir.write("fake_sqs_body", bytes(kwargs.get("MessageBody"), "utf-8"))

    def delete_message(self, **kwargs):
        "follow boto3 sqs client format, delete list item with matching ReceiptHandle value"
        queue_url_response = self.get_queue_url(QueueName=kwargs.get("QueueUrl"))
        queue = self.queues.get(queue_url_response.get("QueueUrl"))
        if queue and queue.messages:
            queue.messages[0]["Messages"] = [
                q_message
                for q_message in queue.messages[0]["Messages"]
                if q_message.get("ReceiptHandle") != kwargs.get("ReceiptHandle")
            ]

    def change_message_visibility(self, **kwargs):
        pass


class FakeSQSQueue:
    def __init__(self, directory, messages=None):
        self.dir = directory
        self.messages = []
        if messages:
            self.messages = messages


class FakeStsClient:
    "mock AWS STS client"

    def assume_role(self, *args, **kwargs):
        "mock response of client.assume_role()"
        return {
            "Credentials": {
                "AccessKeyId": "id",
                "SecretAccessKey": "key",
                "SessionToken": "token",
            },
        }


class FakeFTP:
    def __init__(self, ftp_instance=None):
        self.ftp_instance = ftp_instance

    def ftp_connect(self, **kwargs):
        return self.ftp_instance

    def ftp_cwd_mkd(self, ftp_instance, sub_dir):
        pass

    def ftp_to_endpoint(self, **kwargs):
        pass

    def ftp_upload(self, ftp_instance, filename):
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
    def __init__(
        self,
        directory=data.ExpandArticle_files_source_folder,
        resources=None,
        dest_folder=data.ExpandArticle_files_dest_folder,
    ):
        "can instantiate specifying a data directory or use the default"
        self.dir = directory
        self.resources = [
            "elife-00353-fig1-v1.tif",
            "elife-00353-v1.pdf",
            "elife-00353-v1.xml",
        ]
        if resources is not None:
            self.resources = resources
        self.dest_folder = dest_folder

    def s3_storage_objects(self, resource):
        p = re.compile(r"(.*?)://(.*?)(/.*)")
        match = p.match(resource)
        protocol = match.group(1)
        bucket_name = match.group(2)
        s3_key = match.group(3)
        return bucket_name, s3_key

    def get_resource_attributes(self, resource):
        attributes = {"LastModified": datetime(2021, 1, 1, 0, 0, 1)}
        return attributes

    def resource_exists(self, resource):
        "check if a key exists"
        bucket, s3_key = self.s3_storage_objects(resource)
        src = self.dir + s3_key
        return os.path.exists(src)

    def get_resource_to_file(self, resource, filelike):
        bucket_name, s3_key = self.s3_storage_objects(resource)
        src = self.dir + s3_key
        with open(src, "rb") as fsrc:
            filelike.write(fsrc.read())

    def get_resource_as_string(self, origin):
        bucket_name, s3_key = self.s3_storage_objects(origin)
        src = self.dir + s3_key
        if os.path.exists(src):
            with open(src, "rb") as fsrc:
                return fsrc.read()
        # default used by verify glencoe tests
        return '<mock><media content-type="glencoe play-in-place height-250 width-310" id="media1" mime-subtype="wmv" mimetype="video" xlink:href="elife-00569-media1.wmv"></media></mock>'

    def set_resource_from_filename(self, resource, file_name, metadata=None):
        "resource name can be different than the file name"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        origin_file_name = s3_key.lstrip("/")
        destination_path = os.path.join(self.dest_folder, origin_file_name)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        copy(file_name, destination_path)

    def set_resource_from_string(self, resource, data, content_type=None):
        bucket_name, s3_key = self.s3_storage_objects(resource)
        origin_file_name = s3_key.lstrip("/")
        destination_path = os.path.join(self.dest_folder, origin_file_name)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, "wb") as open_file:
            try:
                open_file.write(data)
            except TypeError:
                if isinstance(data, BytesIO):
                    open_file.write(data.read())
                else:
                    open_file.write(bytes(data, encoding="utf8"))

    def list_resources(self, resource, return_keys=False):
        return self.resources

    def copy_resource(self, origin, destination, additional_dict_metadata=None):
        origin_bucket_name, s3_key = self.s3_storage_objects(origin)
        origin_file_name = s3_key.lstrip("/")
        destination_bucket_name, s3_key = self.s3_storage_objects(destination)
        destination_file_name = s3_key.lstrip("/")
        origin_path = os.path.join(self.dir, origin_file_name)
        destination_path = os.path.join(self.dest_folder, destination_file_name)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        copy(origin_path, destination_path)

    def delete_resource(self, resource):
        "delete from the destination folder"
        bucket_name, s3_key = self.s3_storage_objects(resource)
        file_name = self.dir + "/" + s3_key
        if os.path.exists(file_name):
            os.remove(file_name)


def fake_get_tmp_dir(path=None):
    tmp = "tests/tmp/"
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
    def __init__(self, status_code, response_json=None, text="", content=None):
        self.status_code = status_code
        self.response_json = response_json
        self.content = content
        self.text = text
        self.request = FakeRequest()
        self.headers = {}

    def json(self):
        return self.response_json


class FakeFileInfo:
    def __init__(self):
        self.key = None


class FakeLogger:
    def __init__(self):
        self.logdebug = "First logger debug"
        self.loginfo = ["First logger info"]
        self.logexception = "First logger exception"
        self.logerror = "First logger error"
        self.logwarning = "First logger warning"

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
FakeLaxProvider.get_xml_file_name = MagicMock(return_value="fake.xml")


class FakeGithub:
    "mock object for github.Github"

    def get_user(self, login):
        return FakeGithubNamedUser()


class FakeGithubNamedUser:
    "mock object for github.NamedUser.NamedUser"

    def get_repo(self, full_name_or_id):
        return FakeGithubRepository()


class FakeGithubRepository:
    "mock object for github.Repository.Repository"

    def get_contents(self, path):
        return FakeGithubContentFile()

    def get_git_blob(self, sha):
        return FakeGithubGitBlob()

    def update_file(
        self, path, message, content, sha, branch=None, committer=None, author=None
    ):
        pass

    def create_file(
        self, path, message, content, branch=None, committer=None, author=None
    ):
        pass

    def get_issues(self, *args, **kwargs):
        pass


class FakeGithubContentFile:
    "mock object for github.ContentFile.ContentFile"

    def __init__(self, encoding="base64"):
        self.decoded_content = b"<article/>"
        self.sha = "sha"
        self.encoding = encoding


class FakeGithubGitBlob:
    "mock object for github.GitBlob.GitBlob"

    def __init__(self):
        self.content = b"PGFydGljbGUvPg=="  # base64.b64encode(b"<article/>")
        self.sha = "sha"


class FakeIssueComment:
    "mock object for github.IssueComment.IssueComment"

    def __init__(self, body):
        self.body = body


class FakeGithubIssue:
    "mock object for github.Issue.Issue"

    def __init__(self, title=None, number=None):
        self.title = title
        self.number = number
        self.comment = None
        self.assignees = []
        self.labels = []

    def __repr__(self) -> str:
        return "{class_name}({params})".format(
            class_name=self.__class__.__name__,
            params=", ".join(['title="%s"' % self.title, "number=%d" % self.number]),
        )

    def create_comment(self, body):
        self.comment = FakeIssueComment(body)
        return self.comment

    def remove_from_assignees(self, named_user):
        self.assignees = [
            assignee for assignee in self.assignees if assignee != named_user
        ]

    def add_to_labels(self, label):
        if label not in self.labels:
            self.labels.append(label)
