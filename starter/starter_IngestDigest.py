import json
from provider import utils
from S3utility.s3_notification_info import S3NotificationInfo
from starter.objects import Starter, default_workflow_params
import starter.starter_helper as helper
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF IngestDigest starter
"""


class starter_IngestDigest(Starter):

    def __init__(self, settings=None, logger=None):
        super(starter_IngestDigest, self).__init__(
            settings, logger)
        self.const_name = "IngestDigest"
        # logging
        if not self.logger:
            self.logger = helper.get_starter_logger(
                self.settings.setLevel, helper.get_starter_identity(self.const_name))

    def get_workflow_params(self, run, info):
        workflow_params = default_workflow_params(self.settings)
        workflow_params['workflow_id'] = "%s_%s" % (self.const_name,
                                                    info.file_name.replace('/', '_'))
        workflow_params['workflow_name'] = self.const_name
        workflow_params['workflow_version'] = "1"
        workflow_params['execution_start_to_close_timeout'] = str(60 * 15)

        input_data = S3NotificationInfo.to_dict(info)
        input_data['run'] = run
        workflow_params['input'] = json.dumps(input_data, default=lambda ob: None)

        return workflow_params

    def start(self, settings, run, info):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow(run, info)

    def start_workflow(self, run, info):

        if hasattr(info, 'file_name') is False or info.file_name is None:
            raise NullRequiredDataException("filename is Null. Did not get a filename.")

        self.connect_to_swf()

        workflow_params = self.get_workflow_params(run, info)

        # start a workflow execution
        self.logger.info('Starting workflow: %s', workflow_params.get('workflow_id'))
        try:
            self.start_swf_workflow_execution(workflow_params)
        except NullRequiredDataException as null_exception:
            self.logger.exception(null_exception.message)
            raise
        except:
            message = (
                'Exception starting workflow execution for workflow_id %s' %
                workflow_params.get('workflow_id'))
            self.logger.exception(message)
