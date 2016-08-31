import settings as settingsLib
import random
import boto.swf
import log
import json

"""
Amazon SWF VersionControl starter.
"""


class starter_VersionControl():

    def start(self, ENV="dev", info=None):

        settings = settingsLib.get_settings(ENV)

        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        log_file = "starter.log"
        # logFile = None
        logger = log.logger(log_file, settings.setLevel, identity)

        filename = info.file_name

        if filename is None:
            logger.error("Did not get a filename")
            return

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        # Start a workflow execution
        workflow_id = "VersionControl_%s" % filename.replace('/', '_') + str(int(random.random() * 1000))
        workflow_name = "VersionControl"
        workflow_version = "1"
        child_policy = None
        execution_start_to_close_timeout = str(60 * 30)
        workflow_input = json.dumps(info, default=lambda ob: ob.__dict__)

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            logger.info(message)

        except Exception as e:
            message = 'Exception on VersionControl starter ' + e.message
            logger.error(message)