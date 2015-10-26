import random
import json
import StringIO
from S3utility.s3_notification_info import S3NotificationInfo
import activity
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import log
import boto.swf
from provider.article_structure import ArticleInfo
from provider.execution_context import Session
import settings as settings_lib
import yaml
import provider.imageresize as resizer
import os

"""
ResizeImages.py activity
"""


class activity_ResizeImages(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ResizeImages"
        self.version = "1"

        # standard bot activity parameters
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Resize article images"
        self.logger = logger
        self.formats = self.load_formats()
        # TODO : better exception handling

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        session = Session(self.settings)
        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        run = session.get_value(self.get_workflowId(), 'run')

        self.emit_monitor_event(self.settings, article_id, version, run, "Resize Images", "start",
                                "Starting submission resize of images for article " + article_id)

        try:
            expanded_folder_name = session.get_value(self.get_workflowId(), 'expanded_folder')
            cdn_path = article_id

            if self.logger:
                self.logger.info("Converting images for folder %s" % expanded_folder_name)

            # get information on files in the expanded article bucket for notified zip file
            bucket_folder_name = expanded_folder_name
            bucket, file_infos = self.get_file_infos(bucket_folder_name)

            image_count = 0
            for file_info in file_infos:
                image_count += 1
                key = bucket.get_key(file_info.key)
                # see : http://stackoverflow.com/questions/9954521/s3-boto-list-keys-sometimes-returns-directory-key
                if not key.name.endswith("/"):
                    # process each key in the folder
                    self.process_key(key, cdn_path)
            self.emit_monitor_event(self.settings, article_id, version, run, "Resize Images", "end",
                                    "Finished converting images for  " + article_id +
                                    str(image_count) + " images processed ")

        except Exception as e:
            self.logger.exception("Exception when resizing images")
            self.emit_monitor_event(self.settings, article_id, version, run, "Resize Images", "error",
                                    "Error resizing images for article" + article_id + " message:" + e.message)
            return False
        return True

    def get_file_infos(self, folder_name):
        # connect to S3 and obtain the expanded article bucket
        self.conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key,
                                 host=self.settings.s3_hostname)
        bucket = self.conn.get_bucket(self.settings.publishing_buckets_prefix + self.settings.expanded_bucket)

        # get the keys for the files in the folder and return along with a reference to the bucket
        file_infos = bucket.list(folder_name + "/", "/")
        return bucket, file_infos

    def process_key(self, key, cdn_path):
        # determine filename (without folder) and obtain ArticleInfo instance
        filename = key.name.rsplit('/', 1)[1]
        info = ArticleInfo(filename)

        # see if we have any formats available for the file_type of this file
        formats = self.get_formats(info.file_type)
        if formats is not None:
            # generate images for relevant formats
            fp = StringIO.StringIO()
            key.get_file(fp)
            self.generate_images(formats, fp, info, cdn_path)

    def get_formats(self, file_type):
        # look up file_type in pre-parsed formats
        if file_type in self.formats:
            return self.formats[file_type]
        return None

    def generate_images(self, formats, fp, info,  cdn_path):
        # delegate this to module
        try:
            for format_spec_name in formats:
                fp.seek(0)  # rewind the tape
                filename, image = resizer.resize(formats[format_spec_name], fp, info)
                self.store_in_cdn(filename, image,  cdn_path)
        finally:
            fp.close()

    def store_in_cdn(self, filename, image, cdn_path):
        # for now we'l use an S3 bucket
        try:
            cdn_bucket = self.conn.get_bucket(self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket)
            key = Key(cdn_bucket)
            key.key = cdn_path + "/" + filename
            image.seek(0)
            key.set_contents_from_file(image)
        finally:
            image.close()

    @staticmethod
    def load_formats():
        # load the formats from the YAML file
        stream = file('formats.yaml', 'r')
        formats = yaml.load(stream)
        return formats


def main(args):

    """
    This sets up dummy SWF activity data, creates an instance of this activity and runs it only for
    testing and debugging. This activity would usually be executed by worker.py
    """

    data = None

    settings = settings_lib.get_settings('exp')
    identity = "resize_%s" % int(random.random() * 1000)
    log_file = "worker.log"
    logger = log.logger(log_file, settings.setLevel, identity)
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    act = activity_ResizeImages(settings, logger, conn=conn)
    act.do_activity(data)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
