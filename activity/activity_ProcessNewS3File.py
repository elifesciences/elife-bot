import json
import importlib
import yaml
import re
import activity
import os
from S3utility.s3_notification_info import S3NotificationInfo
import starter

"""
ConvertJATS.py activity
"""
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

class activity_ProcessNewS3File(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ProcessNewS3File"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Process a newly arrived S3 file"
        self.rules = []
        self.info = None
        self.logger = logger
        # TODO : better exception handling

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.info = S3NotificationInfo.from_dict(data)

        if self.logger:
            self.logger.info("File %s has arrived, deciding workflow" % self.info.file_name)

        self.load_rules()

        starter_name = self.get_starter_name()
        module_name = 'starter.' + starter_name
        if module_name is None:
            self.logger.info("Could not handle file %s in bucket %s" % (self.info.file_name, self.info.bucket_name))
            return False
        module = importlib.import_module(module_name)
        try:
            reload(eval(module))
        except:
            pass
        full_path = "starter." + starter_name + "." + starter_name + "()"
        s = eval(full_path)
        s.start(ENV=self.settings.__name__, info=self.info)

        return True

    def load_rules(self):
        # load the rules from the YAML file
        stream = file('newFileWorkflows.yaml', 'r')
        self.rules = yaml.load(stream)

    def get_starter_name(self):
        for rule_name in self.rules:
            rule = self.rules[rule_name]
            if re.match(rule['bucket_name_pattern'], self.info.bucket_name) and \
               re.match(rule['file_name_pattern'], self.info.file_name):
                    return rule['starter_name']
        pass
