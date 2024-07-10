import datetime
import os
from io import BytesIO
import unittest
from mock import MagicMock, patch
from testfixtures import TempDirectory
import botocore
from provider.storage_provider import (
    storage_context,
    S3StorageContext,
    UnsupportedResourceType,
)
from tests import settings_mock


class FakeS3Client:
    def __init__(self, list_objects_responses=None):
        self.object = BytesIO()
        self.object_metadata = None
        self.list_objects_responses = list_objects_responses
        # to increment how many times list_objects_v2() is called
        self.list_objects_counter = 0

    def head_object(self, **kwargs):
        "return an object response dict example"
        return {"AcceptRanges": "string", "ContentLength": 123}

    def download_fileobj(self, **kwargs):
        if (
            kwargs.get("Fileobj")
            and hasattr(kwargs.get("Fileobj"), "writable")
            and kwargs.get("Fileobj").writable()
        ):
            kwargs.get("Fileobj").write(b"example")

    def upload_file(self, **kwargs):
        if kwargs.get("Filename"):
            with open(kwargs.get("Filename"), "rb") as open_file:
                self.object.write(open_file.read())
        if kwargs.get("ExtraArgs") and kwargs.get("ExtraArgs").get("ContentType"):
            self.object_metadata = {
                "Content-Type": kwargs.get("ExtraArgs").get("ContentType")
            }

    def put_object(self, **kwargs):
        if kwargs.get("Body"):
            self.object.write(kwargs.get("Body"))
        if kwargs.get("ContentType"):
            self.object_metadata = {"Content-Type": kwargs.get("ContentType")}

    def list_objects_v2(self, **kwargs):
        if not self.list_objects_responses:
            return {}
        try:
            response = self.list_objects_responses[self.list_objects_counter]
            if kwargs.get("ContinuationToken"):
                response["ContinuationToken"] = kwargs.get("ContinuationToken")
            self.list_objects_counter += 1
            return response
        except IndexError:
            return {}

    def delete_object(self, **kwargs):
        pass


class TestStorageContext(unittest.TestCase):
    def test_storage_context_instatiation(self):
        storage = storage_context(settings_mock)
        self.assertTrue(isinstance(storage, S3StorageContext))


class TestGetClientFromCache(unittest.TestCase):
    @patch.object(S3StorageContext, "get_client")
    def test_get_client_from_cache(self, fake_get_client):
        fake_get_client.return_value = True
        storage = S3StorageContext(settings_mock)
        storage.get_client_from_cache()
        self.assertIsNotNone(storage.context.get("client"))


class TestS3StorageObjects(unittest.TestCase):
    def test_s3_storage_objects(self):
        bucket = "bucket"
        path = "/folder/file.txt"
        resource = "s3://%s%s" % (bucket, path)
        storage = S3StorageContext(settings_mock)
        bucket_name, s3_key = storage.s3_storage_objects(resource)
        self.assertEqual(bucket_name, bucket)
        self.assertEqual(s3_key, path)

    def test_s3_storage_objects_unsupported(self):
        resource = "file://bucket/folder/file.txt"
        storage = S3StorageContext(settings_mock)
        with self.assertRaises(UnsupportedResourceType):
            storage.s3_storage_objects(resource)


class TestResourceExists(unittest.TestCase):
    @patch("boto3.client")
    def test_resource_exists(self, fake_s3_client):
        fake_s3_client.return_value = FakeS3Client()
        storage = S3StorageContext(settings_mock)
        result = storage.resource_exists("s3://a/1")
        self.assertEqual(result, True)

    @patch.object(FakeS3Client, "head_object")
    @patch("boto3.client")
    def test_resource_exists_exception(self, fake_s3_client, fake_head_object):
        fake_s3_client.return_value = FakeS3Client()
        fake_head_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "operation_name",
        )
        storage = S3StorageContext(settings_mock)
        result = storage.resource_exists("s3://a/1")
        self.assertEqual(result, False)


class TestGetResourceAsString(unittest.TestCase):
    @patch("boto3.client")
    def test_get_resource_as_string(self, fake_s3_client):
        fake_s3_client.return_value = FakeS3Client()
        storage = S3StorageContext(settings_mock)
        result = storage.get_resource_as_string("s3://a/1")
        self.assertEqual(result, b"example")


class TestGetResourceToFile(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_get_resource_to_file(self, fake_s3_client):
        directory = TempDirectory()
        test_file_path = os.path.join(directory.path, "test_object")
        fake_s3_client.return_value = FakeS3Client()
        storage = S3StorageContext(settings_mock)
        with open(test_file_path, "wb") as open_file:
            storage.get_resource_to_file("s3://a/1", open_file)
        with open(test_file_path, "rb") as open_file:
            self.assertEqual(open_file.read(), b"example")


class TestGetResourceAttributes(unittest.TestCase):
    @patch("boto3.client")
    def test_get_resource_attributes(self, fake_s3_client):
        fake_s3_client.return_value = FakeS3Client()
        storage = S3StorageContext(settings_mock)
        result = storage.get_resource_attributes("s3://a/1")
        self.assertTrue(isinstance(result, dict))


class TestSetResourceFromFilename(unittest.TestCase):
    "tests for set_resource_from_filename()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("boto3.client")
    def test_set_resource_from_filename(self, fake_s3_client):
        directory = TempDirectory()
        test_file_path = os.path.join(directory.path, "test_object")
        test_value = b"example"
        test_metadata = {"ContentType": "image/jpeg"}
        expected_metadata = {"Content-Type": "image/jpeg"}
        with open(test_file_path, "wb") as open_file:
            open_file.write(test_value)
        s3_client = FakeS3Client()
        fake_s3_client.return_value = s3_client
        storage = S3StorageContext(settings_mock)
        storage.set_resource_from_filename("s3://a/1", test_file_path, test_metadata)
        self.assertEqual(s3_client.object.getvalue(), test_value)
        self.assertEqual(s3_client.object_metadata, expected_metadata)

    @patch("boto3.client")
    def test_no_metadata(self, fake_s3_client):
        "test if no metadata argument is passed"
        directory = TempDirectory()
        test_file_path = os.path.join(directory.path, "test_object")
        test_value = b"example"
        with open(test_file_path, "wb") as open_file:
            open_file.write(test_value)
        s3_client = FakeS3Client()
        fake_s3_client.return_value = s3_client
        storage = S3StorageContext(settings_mock)
        storage.set_resource_from_filename("s3://a/1", test_file_path)
        self.assertEqual(s3_client.object.getvalue(), test_value)
        self.assertEqual(s3_client.object_metadata, None)


class TestSetResourceFromString(unittest.TestCase):
    @patch("boto3.client")
    def test_set_resource_from_string(self, fake_s3_client):
        test_value = b"example"
        test_content_type = "image/jpeg"
        s3_client = FakeS3Client()
        fake_s3_client.return_value = s3_client
        storage = S3StorageContext(settings_mock)
        storage.set_resource_from_string("s3://a/1", test_value, test_content_type)
        self.assertEqual(s3_client.object.getvalue(), test_value)
        self.assertEqual(
            s3_client.object_metadata, {"Content-Type": "%s" % test_content_type}
        )


class TestListResources(unittest.TestCase):
    def setUp(self):
        # multiple responses returned by the client
        self.list_objects_responses = [
            {
                "IsTruncated": True,
                "NextContinuationToken": "token",
                "Contents": [
                    {
                        "Key": "key1",
                        "LastModified": datetime.datetime(2015, 1, 1),
                        "ETag": "etag1",
                        "Size": 123,
                    },
                ],
            },
            {
                "Contents": [
                    {
                        "Key": "key2",
                        "LastModified": datetime.datetime(2015, 1, 1),
                        "ETag": "etag2",
                        "Size": 123,
                    },
                ],
            },
        ]

    @patch("boto3.client")
    def test_list_resources(self, fake_s3_client):
        fake_s3_client.return_value = FakeS3Client(self.list_objects_responses)
        storage = S3StorageContext(settings_mock)
        result = storage.list_resources("s3://a/1")
        self.assertEqual(result, ["key1", "key2"])

    @patch("boto3.client")
    def test_list_resources_return_keys(self, fake_s3_client):
        fake_s3_client.return_value = FakeS3Client(self.list_objects_responses)
        storage = S3StorageContext(settings_mock)
        result = storage.list_resources("s3://a/1", return_keys=True)
        self.assertEqual(
            result,
            [
                {
                    "Key": "key1",
                    "LastModified": datetime.datetime(2015, 1, 1, 0, 0),
                    "ETag": "etag1",
                    "Size": 123,
                },
                {
                    "Key": "key2",
                    "LastModified": datetime.datetime(2015, 1, 1, 0, 0),
                    "ETag": "etag2",
                    "Size": 123,
                },
            ],
        )


class TestCopyResource(unittest.TestCase):
    def setUp(self):
        self.storage = S3StorageContext(settings_mock)
        self.storage.context["client"] = MagicMock()

    def test_copy_without_any_metadata_to_override(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(original, destination, None)
        self.storage.context["client"].copy_object.assert_called()
        self.assertDictEqual(
            {
                "Bucket": "b",
                "CopySource": {"Bucket": "a", "Key": "1"},
                "Key": "2",
                "RequestPayer": "requester",
            },
            self.storage.context["client"].copy_object.mock_calls[0][2],
        )

    def test_copy_and_specify_metadata(self):
        original = "s3://a/1"
        destination = "s3://b/2"
        self.storage.copy_resource(
            original,
            destination,
            {
                "Content-Type": "application/json",
                "Content-Disposition": "Content-Disposition: attachment; filename=2;",
            },
        )
        self.assertDictEqual(
            {
                "CopySource": {"Bucket": "a", "Key": "1"},
                "Bucket": "b",
                "Key": "2",
                "MetadataDirective": "REPLACE",
                "ContentType": "application/json",
                "ContentDisposition": "Content-Disposition: attachment; filename=2;",
                "RequestPayer": "requester",
            },
            self.storage.context["client"].copy_object.mock_calls[0][2],
        )


class TestDeleteResourceFromString(unittest.TestCase):
    @patch.object(FakeS3Client, "delete_object")
    @patch("boto3.client")
    def test_delete_resource(self, fake_s3_client, fake_delete_object):
        fake_s3_client.return_value = FakeS3Client()
        storage = S3StorageContext(settings_mock)
        fake_delete_object.return_value = MagicMock()
        storage.delete_resource("s3://a/1")
        fake_delete_object.assert_called_with(
            Bucket="a", Key="1", RequestPayer="requester"
        )
