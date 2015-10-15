import activity
import log
import json
import boto
import random
from boto import swf
import zipfile
from datetime import datetime
from time import strftime
import os
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session
import settings as settings_lib

"""
activity_PostEIF.py activity
"""


class activity_ArchiveArticle(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ArchiveArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Archive an article post-publication"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:

            session = Session(self.settings)

            id = data['article_id']
            version = data['version']
            expanded_folder = data['expanded_folder']
            update_date_string = data['update_date']
            updated_date = datetime.strptime(update_date_string, "%Y-%m-%dT%H:%M:%SZ")
            status = data['status'].lower()

            # download expanded folder
            conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
            source_bucket = conn.get_bucket(self.settings.publishing_buckets_prefix + self.settings.expanded_bucket)
            tmp = self.get_tmp_dir()
            name = "/elife-" + id + '-' + status + '-v' + version + '-' + updated_date.strftime('%Y%m%d%H%m%S')
            zip_dir = tmp + name
            os.makedirs(zip_dir)
            folderlist = source_bucket.list(prefix=expanded_folder)
            for key in folderlist:
                save_path = zip_dir+'/'+os.path.basename(key.name)
                key.get_contents_to_filename(save_path)

            # rename downloaded folder
            zip_path = tmp + name + '.zip'
            # zip expanded folder
            zf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            relroot = os.path.abspath(os.path.join(zip_dir, os.pardir))
            for root, dirs, files in os.walk(zip_dir):
                # add directory (needed for empty dirs)
                zf.write(root, os.path.relpath(root, zip_dir))
                for f in files:
                    filename = os.path.join(root, f)
                    if os.path.isfile(filename):
                        arcname = os.path.join(os.path.relpath(root, relroot), f)
                        zf.write(filename, arcname)
            zf.close()

            # upload zip to archive bucket
            output_bucket = self.settings.publishing_buckets_prefix + self.settings.archive_bucket
            destination = conn.get_bucket(output_bucket)
            destination_key = Key(destination)
            destination_key.key = name + '.zip'
            destination_key.set_contents_from_filename(zip_path)

        except Exception as e:
            # TODO: log
            return False

        return True

def main(args):

    """
    This sets up dummy SWF activity data, creates an instance of this activity and runs it only for
    testing and debugging. This activity would usually be executed by worker.py
    """

    data = {
        'id': '00353',
        'expanded_folder': '00353.1/9a0f0b0d-1f0b-47c8-88ef-050bd9cdff92',
        'version': '1',
        'status': 'VOR',
        'updated_date': datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%S")
    }

    settings = settings_lib.get_settings('exp')
    identity = "resize_%s" % int(random.random() * 1000)
    log_file = "worker.log"
    logger = log.logger(log_file, settings.setLevel, identity)
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    act = activity_ArchiveArticle(settings, logger, conn=conn)
    act.do_activity(data)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])