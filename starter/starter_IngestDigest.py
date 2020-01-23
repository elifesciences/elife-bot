import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import json
from provider import utils
from S3utility.s3_notification_info import S3NotificationInfo
import starter.starter_helper as helper
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF IngestDigest starter
"""


class starter_IngestDigest():
    def __init__(self):
        self.const_name = "IngestDigest"

    def start(self, settings, run, info):

        # Log
        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if hasattr(info, 'file_name') is False or info.file_name is None:
            raise NullRequiredDataException("filename is Null. Did not get a filename.")

        input_data = S3NotificationInfo.to_dict(info)
        input_data['run'] = run

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(self.const_name, "1", None, input_data,
                                                         info.file_name.replace('/', '_'),
                                                         start_to_close_timeout=str(60 * 15))

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s', json.dumps(response, sort_keys=True, indent=4))

        except NullRequiredDataException as null_exception:
            logger.exception(null_exception.message)
            raise

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: ' \
                      'There is already a running workflow with ID %s' % workflow_id
            logger.info(message)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER_OBJECT = starter_IngestDigest()

    # note: this starter must be started by an S3Notification and not directly from command line
    RUN = None
    INFO = None
    STARTER_OBJECT.start(settings=SETTINGS, run=RUN, info=INFO)
