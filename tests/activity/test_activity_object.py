# coding=utf-8

import json
import os
import unittest
import botocore
from mock import patch
from testfixtures import TempDirectory
from elifecleaner.transform import ArticleZipFile
import dashboard_queue
from activity.objects import Activity, AcceptedBaseActivity
from tests.activity import settings_mock
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


class TestActivityInit(unittest.TestCase):
    "tests instantiating an object"

    def test_activity_init_with_no_settings(self):
        "test an activity object where some settings are blank"
        test_settings = object
        activity_object = Activity(test_settings, None, None, None, None)
        self.assertEqual(activity_object.domain, None)
        self.assertEqual(activity_object.task_list, None)


class TestActivityDescribe(unittest.TestCase):
    def test_describe(self):
        "test if object has the correct properties to describe itself"
        client = FakeSWFClient()
        activity_object = Activity(settings_mock, FakeLogger(), client, None, None)
        activity_object.domain = "domain"
        activity_object.name = "name"
        activity_object.version = "version"
        result = activity_object.describe()
        self.assertIsNotNone(result.get("typeInfo"))

    @patch("boto3.client")
    def test_describe_no_client(self, fake_client):
        "test if object client property is None"
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        fake_client.return_value = FakeSWFClient()
        result = activity_object.describe()
        self.assertEqual(result, None)

    @patch.object(FakeSWFClient, "describe_activity_type")
    def test_describe_exception(self, fake_describe_activity_type):
        "test if object has the correct properties to describe itself"
        client = FakeSWFClient()
        activity_object = Activity(settings_mock, FakeLogger(), client, None, None)
        activity_object.domain = "domain"
        activity_object.name = "name"
        activity_object.version = "version"
        fake_describe_activity_type.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "UnknownResourceFault"}},
            "operation_name",
        )
        result = activity_object.describe()
        self.assertEqual(result, None)


class TestActivityRegister(unittest.TestCase):
    @patch.object(Activity, "describe")
    def test_register(self, fake_describe):
        "test if object has the correct properties to register itself and describe returns None"
        fake_describe.return_value = None
        client = FakeSWFClient()
        activity_object = Activity(settings_mock, FakeLogger(), client, None, None)
        activity_object.domain = "domain"
        activity_object.name = "name"
        activity_object.version = "version"
        result = activity_object.register()
        self.assertEqual(result, None)

    @patch("boto3.client")
    def test_register_no_client(self, fake_client):
        "test if object client property is None"
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        fake_client.return_value = FakeSWFClient()
        result = activity_object.register()
        self.assertEqual(result, None)


class TestActivityGetWorkflowId(unittest.TestCase):
    def test_get_workflow_id(self):
        "test getting the workflowId from the SWF activity_task"
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
            activity_json = json.loads(open_file.read())
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        activity_object.activity_task = activity_json
        result = activity_object.get_workflowId()
        self.assertEqual(result, "sum_3481")

    def test_get_workflow_id_exception(self):
        "get the workflowId when a dict key is missing"
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        activity_object.activity_task = {}
        result = activity_object.get_workflowId()
        self.assertEqual(result, None)


class TestActivityGetActivityId(unittest.TestCase):
    def test_get_activity_id(self):
        "test getting the activityId from the SWF activity_task"
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
            activity_json = json.loads(open_file.read())
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        activity_object.activity_task = activity_json
        result = activity_object.get_activityId()
        self.assertEqual(result, "Sum2a")

    def test_get_activity_id_none(self):
        "get the activityId when a dict key is missing"
        activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        activity_object.activity_task = {}
        result = activity_object.get_activityId()
        self.assertEqual(result, None)


class TestActivityMakeTmpDir(unittest.TestCase):
    def setUp(self):
        self.activity_object = Activity(settings_mock, FakeLogger(), None, None, None)
        self.domain_original = self.activity_object.settings.domain

    def tearDown(self):
        # reset the settings value
        self.activity_object.settings.domain = self.domain_original
        # clean up the disk
        self.activity_object.clean_tmp_dir()

    def test_make_tmp_dir(self):
        "test creating a temporary directory"
        self.activity_object.make_tmp_dir()
        self.assertIsNotNone(self.activity_object.tmp_dir)

    def test_make_tmp_dir_domain_missing(self):
        "test creating a temporary directory when domain is missing in settings"
        del self.activity_object.settings.domain
        self.activity_object.make_tmp_dir()
        self.assertIsNotNone(self.activity_object.tmp_dir)

    def test_make_tmp_dir_domain_none(self):
        "test creating a temporary directory when domain is not None"
        domain = "domain"
        self.activity_object.settings.domain = domain
        self.activity_object.make_tmp_dir()
        self.assertTrue(self.activity_object.tmp_dir.endswith(domain))

    def test_make_tmp_dir_workflow_id_activity_id(self):
        "test creating a temporary directory containing a workflowId and activityId"
        with open("tests/test_data/activity.json", "r", encoding="utf-8") as open_file:
            activity_json = json.loads(open_file.read())
        self.activity_object.activity_task = activity_json
        self.activity_object.make_tmp_dir()
        self.assertTrue(self.activity_object.tmp_dir.endswith("sum_3481.Sum2a"))

    @patch("os.mkdir")
    def test_make_tmp_dir_exception(self, fake_mkdir):
        "test OSError exception"
        fake_mkdir.side_effect = OSError
        with self.assertRaises(RuntimeError):
            self.activity_object.make_tmp_dir()


class TestActivityDirectories(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = Activity(settings_mock, fake_logger, None, None, None)
        # create a tmp directory before os.mkdir is potentially mocked
        self.activity.make_tmp_dir()

    def tearDown(self):
        self.activity.directories = None
        self.activity.clean_tmp_dir()

    def tmp_dir_folder_name(self, dir_name):
        return os.path.join(self.activity.get_tmp_dir(), dir_name)

    def test_make_activity_directories_none(self):
        "test creating activity directories with None values"
        self.assertIsNone(self.activity.make_activity_directories())

    def test_make_activity_directories_new(self):
        "test creating a new activity directory passed as an argument"
        dir_names = [self.tmp_dir_folder_name("foo"), self.tmp_dir_folder_name("bar")]
        self.assertTrue(self.activity.make_activity_directories(dir_names))

    def test_make_activity_directories_property(self):
        "test creating a new activity directory from object property"
        self.activity.directories = {"foo": self.tmp_dir_folder_name("foo")}
        self.assertTrue(self.activity.make_activity_directories())

    def test_make_activity_directories_bad_property(self):
        "test bad directories object property"
        self.activity.directories = ["list_not_supported_here"]
        self.assertIsNone(self.activity.make_activity_directories())
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "No dir_names to create in make_activity_directories()",
        )

    def test_make_activity_directories_exists(self):
        "test creating a new activity directory passed as an argument"
        dir_name = self.tmp_dir_folder_name("foo")
        os.mkdir(dir_name)
        dir_names = [dir_name]
        self.assertTrue(self.activity.make_activity_directories(dir_names))

    @patch("activity.objects.os.mkdir")
    def test_make_activity_directories_exception(self, fake_mkdir):
        "test creating a new activity directory exception catching"
        dir_names = [self.tmp_dir_folder_name("foo")]
        fake_mkdir.side_effect = OSError("Something went wrong!")
        self.assertRaises(Exception, self.activity.make_activity_directories, dir_names)


class TestEmitActivityMessage(unittest.TestCase):
    @patch.object(Activity, "emit_monitor_event")
    def test_emit_activity_message_exception(self, fake_emit_monitor_event):
        message = "A message"
        exception = "An exception"
        fake_emit_monitor_event.side_effect = Exception(exception)
        logger = FakeLogger()
        activity_object = Activity(settings_mock, logger, None, None, None)
        activity_object.emit_activity_message("666", "1", "run", message, None)
        self.assertEqual(
            logger.logexception,
            "Exception emitting %s message. Details: %s" % (message, exception),
        )


class TestEmitActivityStartMessage(unittest.TestCase):
    @patch.object(dashboard_queue, "send_message")
    def test_emit_activity_start_message(self, fake_send_message):
        fake_send_message.return_value = True
        activity_object = Activity(settings_mock, None, None, None, None)
        activity_object.pretty_name = "Testing a pretty name"
        result = activity_object.emit_activity_start_message("666", "1", "run")
        self.assertEqual(result, True)


class TestEmitActivityEndMessage(unittest.TestCase):
    @patch.object(dashboard_queue, "send_message")
    def test_emit_activity_end_message(self, fake_send_message):
        fake_send_message.return_value = True
        activity_object = Activity(settings_mock, None, None, None, None)
        result = activity_object.emit_activity_end_message("666", "1", "run")
        self.assertEqual(result, True)


class TestEmitMonitorEvent(unittest.TestCase):
    @patch.object(dashboard_queue, "send_message")
    def test_emit_monitor_event(self, fake_send_message):
        fake_send_message.return_value = True
        activity_object = Activity(settings_mock, None, None, None, None)
        result = activity_object.emit_monitor_event(
            settings_mock, "666", None, None, None, None, None
        )
        self.assertIsNone(result)


class TestAddFileTags(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_file_tags(self):
        "test adding file tags to XML"
        directory = TempDirectory()

        input_filename = "30-01-2019-RA-eLife-45644.zip"

        # create XML file
        xml_string = "<article><article-meta><files/></article-meta></article>"
        xml_file_name = "30-01-2019-RA-eLife-45644.xml"
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string)
        # file transformation data
        from_file_name = "local.jpg"
        to_file_name = "elife-45644-sa0-fig1.jpg"
        file_transformations = []
        from_file = ArticleZipFile(from_file_name)
        to_file = ArticleZipFile(to_file_name)
        file_transformations.append((from_file, to_file))
        logger = FakeLogger()

        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        activity_object.add_file_tags(
            xml_file_path, file_transformations, input_filename
        )
        # assertions
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            new_xml_string = open_file.read()
        self.assertTrue(
            (
                "<files>"
                '<file file-type="figure">'
                "<upload_file_nm>%s</upload_file_nm>"
                "</file>"
                "</files>" % to_file_name
            )
            in new_xml_string
        )


class TestSetMonitorProperty(unittest.TestCase):
    @patch.object(dashboard_queue, "send_message")
    def test_set_monitor_property(self, fake_send_message):
        fake_send_message.return_value = True
        activity_object = Activity(settings_mock, None, None, None, None)
        result = activity_object.set_monitor_property(
            settings_mock, "666", None, None, None
        )
        self.assertIsNone(result)


class TestAcceptedExpandedResourcePrefix(unittest.TestCase):
    def test_accepted_expanded_resource_prefix(self):
        expanded_folder = "expanded"
        expected = "s3://bot_bucket/expanded"
        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, None, None, None, None)
        # invoke
        result = activity_object.accepted_expanded_resource_prefix(expanded_folder)
        self.assertEqual(result, expected)


class TestCopyExpandedFolderFiles(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_copy(self):
        "test copying objects in the bucket folder"
        directory = TempDirectory()
        # add a file to the directory
        from_file_name = "elife-87356-inf1.jpg"
        to_file_name = "elife-87356-sa3-fig1.jpg"
        with open(os.path.join(directory.path, from_file_name), "w") as open_file:
            open_file.write("")

        # asset map
        resource_prefix = "s3://bot-bucket/"
        asset_file_name_map = {
            from_file_name: "%s%s" % (from_file_name, resource_prefix)
        }

        # files to transform
        file_transformations = []
        from_file = ArticleZipFile(from_file_name)
        to_file = ArticleZipFile(to_file_name)
        file_transformations.append((from_file, to_file))
        resources = [from_file_name]
        storage = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        logger = FakeLogger()
        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        result = activity_object.copy_expanded_folder_files(
            asset_file_name_map, resource_prefix, file_transformations, storage
        )
        # assertions
        self.assertEqual(result, True)
        self.assertEqual(len(os.listdir(directory.path)), 2)
        self.assertEqual(
            sorted(os.listdir(directory.path)), [from_file_name, to_file_name]
        )

    def test_blank_value(self):
        "test if one of the file names is blank"
        directory = TempDirectory()
        from_file_name = "elife-87356-inf1.jpg"
        to_file_name = None
        file_transformations = []
        from_file = ArticleZipFile(from_file_name)
        to_file = ArticleZipFile(to_file_name)
        file_transformations.append((from_file, to_file))
        # asset map
        asset_file_name_map = {}
        resource_prefix = ""
        storage = FakeStorageContext(directory.path, [], dest_folder=directory.path)
        logger = FakeLogger()
        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        with self.assertRaises(RuntimeError):
            result = activity_object.copy_expanded_folder_files(
                asset_file_name_map, resource_prefix, file_transformations, storage
            )
            self.assertEqual(result, activity_object.ACTIVITY_PERMANENT_FAILURE)


class TestRenameExpandedFolderFiles(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_rename(self):
        "test renaming objects in the bucket folder"
        directory = TempDirectory()
        # add a file to the directory
        from_file_name = "elife-87356-inf1.jpg"
        to_file_name = "elife-87356-sa3-fig1.jpg"
        with open(os.path.join(directory.path, from_file_name), "w") as open_file:
            open_file.write("")

        # asset map
        resource_prefix = "s3://bot-bucket/"
        asset_file_name_map = {
            from_file_name: "%s%s" % (resource_prefix, from_file_name)
        }

        # files to transform
        file_transformations = []
        from_file = ArticleZipFile(from_file_name)
        to_file = ArticleZipFile(to_file_name)
        file_transformations.append((from_file, to_file))
        resources = [from_file_name]
        storage = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        logger = FakeLogger()

        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        result = activity_object.rename_expanded_folder_files(
            asset_file_name_map, resource_prefix, file_transformations, storage
        )
        # assertions
        self.assertEqual(result, True)
        self.assertEqual(os.listdir(directory.path), [to_file_name])

    def test_blank_value(self):
        "test if one of the file names is blank"
        directory = TempDirectory()
        from_file_name = "elife-87356-inf1.jpg"
        to_file_name = None
        file_transformations = []
        from_file = ArticleZipFile(from_file_name)
        to_file = ArticleZipFile(to_file_name)
        file_transformations.append((from_file, to_file))
        # asset map
        resource_prefix = "s3://bot-bucket/"
        asset_file_name_map = {
            from_file_name: "%s%s" % (resource_prefix, from_file_name)
        }

        resources = [from_file_name]
        storage = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        logger = FakeLogger()
        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        with self.assertRaises(RuntimeError):
            result = activity_object.rename_expanded_folder_files(
                asset_file_name_map, resource_prefix, file_transformations, storage
            )
            self.assertEqual(result, activity_object.ACTIVITY_PERMANENT_FAILURE)


class TestDeleteExpandedFolderFiles(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_delete(self):
        "test deleting objects in the bucket folder"
        directory = TempDirectory()
        # add a file to the directory
        from_file_name = "elife-87356-inf1.jpg"
        with open(os.path.join(directory.path, from_file_name), "w") as open_file:
            open_file.write("")

        # asset map
        resource_prefix = "s3://bot-bucket/"
        asset_file_name_map = {
            from_file_name: "%s%s" % (resource_prefix, from_file_name)
        }

        resources = [from_file_name]
        storage = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        logger = FakeLogger()
        # files to delete
        file_name_list = [from_file_name]

        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        activity_object.delete_expanded_folder_files(
            asset_file_name_map, resource_prefix, file_name_list, storage
        )
        # assertions
        self.assertEqual(len(os.listdir(directory.path)), 0)

    @patch.object(FakeStorageContext, "delete_resource")
    def test_blank_value(self, fake_delete):
        "test if the S3 object cannot be deleted"
        fake_delete.side_effect = Exception("An exception")
        directory = TempDirectory()
        from_file_name = "elife-87356-inf1.jpg"
        file_name_list = [from_file_name]
        # asset map
        resource_prefix = "s3://bot-bucket/"
        asset_file_name_map = {
            from_file_name: "%s%s" % (resource_prefix, from_file_name)
        }
        resources = [from_file_name]
        storage = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        logger = FakeLogger()
        # instantiate
        activity_object = AcceptedBaseActivity(settings_mock, logger, None, None, None)
        # invoke
        with self.assertRaises(Exception):
            activity_object.delete_expanded_folder_files(
                asset_file_name_map, resource_prefix, file_name_list, storage
            )
