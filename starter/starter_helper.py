import os
import json
import importlib
import log

class NullRequiredDataException(Exception):
    def __init__(self, message):
        self.message = message


def get_starter_identity(name):
    return "starter_" + name + "." + str(os.getpid())


def get_starter_logger(set_level, identity, log_file="starter.log"):
    return log.logger(log_file, set_level, identity)


def set_workflow_information(
    name,
    workflow_version,
    child_policy,
    data,
    workflow_id_part,
    extra="",
    start_to_close_timeout=str(60 * 30),
):
    workflow_id = "%s_%s" % (name, workflow_id_part)
    if extra:
        workflow_id = workflow_id + (".%s" % extra)
    workflow_name = name
    workflow_version = workflow_version
    child_policy = child_policy
    execution_start_to_close_timeout = start_to_close_timeout
    workflow_input = json.dumps(data, default=lambda ob: None)

    return (
        workflow_id,
        workflow_name,
        workflow_version,
        child_policy,
        execution_start_to_close_timeout,
        workflow_input,
    )


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
        logger.exception(
            "Failed to instantiate a starter module object for %s" % starter_name
        )


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
            logger.exception("Failed to import a starter module %s" % starter_name)
        return False


def start_ping_marker(workflow_id, settings, logger):
    """
    Start a ping workflow with a unique name to serve as a time marker
    for determining last time workflow_id was run
    """

    workflow_id = workflow_id
    workflow_name = "Ping"
    workflow_version = "1"
    execution_start_to_close_timeout = None
    workflow_input = None

    kwargs = {
        "domain": settings.domain,
        "workflowId": workflow_id,
        "workflowType": {
            "name": workflow_name,
            "version": workflow_version,
        },
        "taskList": {"name": settings.default_task_list},
    }
    if workflow_input:
        kwargs["input"] = workflow_input
    if execution_start_to_close_timeout:
        kwargs["executionStartToCloseTimeout"] = execution_start_to_close_timeout

    client = settings.aws_conn('swf', {
        'aws_access_key_id': settings.aws_access_key_id,
        'aws_secret_access_key': settings.aws_secret_access_key,
        'region_name': settings.swf_region,
    })

    try:
        # Try and start a workflow
        client.start_workflow_execution(**kwargs)

    except Exception as exception:
        message = "%s exception starting workflow %s: %s" % (
            "starter_helper",
            workflow_id,
            str(exception),
        )
        logger.exception(message)
