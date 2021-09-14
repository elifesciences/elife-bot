import boto.swf
import json
from S3utility.s3_notification_info import S3NotificationInfo
import starter.starter_helper as helper
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF IngestArticleZip starter, preparing article xml for lax.
"""


class starter_IngestArticleZip():
    def __init__(self):
        self.const_name = "IngestArticleZip"
        
    def start(self, settings, run, info):

        # Log
        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if hasattr(info, 'file_name') == False or info.file_name is None:
            raise NullRequiredDataException("filename is Null. Did not get a filename.")

        input = S3NotificationInfo.to_dict(info)
        input['run'] = run
        input['version_lookup_function'] = "article_next_version"
        input['run_type'] = "initial-article"

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(self.const_name, "1", None, input,
                                                         info.file_name.replace('/', '_'),
                                                         start_to_close_timeout=str(60 * 60 * 1))

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
            message = 'SWFWorkflowExecutionAlreadyStartedError: ' \
                      'There is already a running workflow with ID %s' % workflow_id
            logger.info(message)
