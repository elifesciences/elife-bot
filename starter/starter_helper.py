import os
import json
import importlib
import boto
import log


class NullRequiredDataException(Exception):
    def __init__(self, message):
        self.message = message


def get_starter_identity(name):
    return "starter_" + name + "." + str(os.getpid())


def get_starter_logger(set_level, identity, log_file="starter.log"):
    return log.logger(log_file, set_level, identity)


def set_workflow_information(name, workflow_version, child_policy, data, workflow_id_part,
                             extra="", start_to_close_timeout=str(60 * 30)):
    workflow_id = "%s_%s" % (name, workflow_id_part)
    if extra:
        workflow_id = workflow_id + (".%s" % extra)
    workflow_name = name
    workflow_version = workflow_version
    child_policy = child_policy
    execution_start_to_close_timeout = start_to_close_timeout
    workflow_input = json.dumps(data, default=lambda ob: None)

    return workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input


def get_starter_module(starter_name, logger):
    """
    Given an starter_name, and if the starter module is already
    imported, load the module and return it
    """
    module_name = "starter." + starter_name
    try:
        module_object = importlib.import_module(module_name)
        starter_class = getattr(module_object, starter_name)
        # Create the object
        starter_object = starter_class()
        return starter_object
    except ImportError:
        logger.exception('')


def import_starter_module(starter_name, logger):
    """
    Given an starter name as starter_name,
    attempt to lazy load the module when needed
    """
    try:
        module_name = "starter." + starter_name
        importlib.import_module(module_name)
        return True
    except ImportError:
        if logger:
            logger.exception('')
        return False


def start_ping_marker(workflow_id, settings, logger):
    """
    Start a ping workflow with a unique name to serve as a time marker
    for determining last time workflow_id was run
    """

    workflow_id = workflow_id
    workflow_name = "Ping"
    workflow_version = "1"
    child_policy = None
    execution_start_to_close_timeout = None
    workflow_input = None

    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    try:
        conn.start_workflow_execution(
            settings.domain, workflow_id, workflow_name,
            workflow_version, settings.default_task_list,
            child_policy, execution_start_to_close_timeout,
            workflow_input)

    except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
        # There is already a running workflow with that ID, cannot start another
        message = (
            'SWFWorkflowExecutionAlreadyStartedError: There is already ' +
            'a running workflow with ID %s' % workflow_id)
        logger.exception(message)
