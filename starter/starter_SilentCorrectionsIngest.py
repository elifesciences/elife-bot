import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import json
from optparse import OptionParser
from S3utility.s3_notification_info import S3NotificationInfo
import starter_helper as helper
from starter_helper import NullRequiredDataException

"""
Amazon SWF SilentCorrectionsIngest starter, preparing article xml for lax.
"""


class starter_SilentCorrectionsIngest():
    def __init__(self):
        self.const_name = "SilentCorrectionsIngest"

    def start(self, settings, info=None, run=None):

        # Log
        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if hasattr(info, 'file_name') == False or info.file_name is None:
            raise NullRequiredDataException("filename is Null / Did not get a filename.")

        input = S3NotificationInfo.to_dict(info)
        input['run'] = run
        input['version_lookup_function'] = "article_highest_version"
        input['force'] = True

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(self.const_name, "1", None, input,
                                                         info.file_name.replace('/', '_'), os.getpid())

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except NullRequiredDataException as e:
            logger.exception(e.message)
            raise

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            logger.info(message)


if __name__ == "__main__":

    doi_id = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    parser.add_option("-f", "--filename", default=None, action="store", type="string", dest="filename",
                      help="specify the DOI id the article to process")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.filename:
        filename = options.filename

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_SilentCorrectionsIngest()

    o.start(settings=settings,)