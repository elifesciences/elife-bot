import os
import copy
import json
import importlib
from botocore.config import Config
from provider import process, utils
from log import create_log
import workflow


def decide(settings, flag, debug=False):
    # Decider event history length requested
    maximum_page_size = 100

    # Log
    identity = "decider_%s" % os.getpid()
    log_file = "decider.log"
    logger = create_log(log_file, settings.setLevel, identity)

    # Simple connect
    client = settings.aws_conn('swf', {
        'aws_access_key_id': settings.aws_access_key_id,
        'aws_secret_access_key': settings.aws_secret_access_key,
        'region_name': settings.swf_region,
        'config': Config(connect_timeout=50, read_timeout=70),
    })

    token = None

    # Poll for a decision task
    while flag.green():
        if token is None:
            logger.info("polling for decision...")

            decision = client.poll_for_decision_task(
                domain=settings.domain,
                taskList={"name": settings.default_task_list},
                identity=identity,
                maximumPageSize=maximum_page_size,
            )

            # Check for a nextPageToken and keep polling until all events are pulled
            decision = get_all_paged_events(
                decision,
                client,
                settings.domain,
                settings.default_task_list,
                identity,
                maximum_page_size,
            )

            token = get_task_token(decision)
            logger.info("got token: %s", token)

            decision_to_log = trimmed_decision(decision, debug)

            if (
                isinstance(decision, dict)
                and "startedEventId" in decision
                and decision["startedEventId"] == 0
            ):
                logger.debug(
                    "got decision: \n%s",
                    json.dumps(decision_to_log, sort_keys=True, indent=4),
                )
            else:
                logger.info(
                    "got decision: \n%s",
                    json.dumps(decision_to_log, sort_keys=True, indent=4),
                )

            if token is not None:
                workflow_type = get_workflow_type(decision)
                process_workflow(
                    workflow_type,
                    decision,
                    settings,
                    logger,
                    client,
                    token,
                    maximum_page_size,
                )

        # Reset and loop
        token = None

    logger.info("graceful shutdown")


def process_workflow(
    workflow_type, decision, settings, logger, client, token, maximum_page_size
):
    """for each decision token load the workflow and run it"""
    # for the workflowType attempt to do the work
    if workflow_type is not None:

        logger.info("workflowType: %s", workflow_type)

        # Instantiate and object for the workflow using eval
        # Build a string for the object name
        workflow_name = get_workflow_name(workflow_type)

        # Attempt to import the module for the workflow
        if import_workflow_class(workflow_name):
            # Instantiate the workflow object
            workflow_object = get_workflow_object(
                workflow_name,
                settings,
                logger,
                client,
                token,
                decision,
                maximum_page_size,
            )
            # Process the workflow
            invoke_do_workflow(workflow_name, workflow_object, logger)
        else:
            logger.info("error: could not load object %s\n", workflow_name)


def invoke_do_workflow(workflow_name, workflow_object, logger):
    """given workflow name and object process it by calling do_workflow()"""
    try:
        success = workflow_object.do_workflow()
    except Exception:
        success = None
        logger.error("error processing workflow %s", workflow_name, exc_info=True)

    # Print the result to the log
    if success:
        logger.info("%s success %s" % (workflow_name, success))


def trimmed_decision(decision, debug=False):
    """trim data from a copy of decision prior to logging if not debug"""
    decision_trimmed = copy.deepcopy(decision)
    if not debug:
        # removed to limit verbosity
        decision_trimmed["events"] = []
    return decision_trimmed


def get_all_paged_events(
    decision, client, domain, task_list, identity, maximum_page_size
):
    """
    Given a poll_for_decision_task response, check if there is a nextPageToken
    and if so, recursively poll for all workflow events, and assemble a final
    decision response to return
    """

    # First check if there is no nextPageToken, if there is none
    #  return the decision, nothing to page
    next_page_token = None
    try:
        next_page_token = decision["nextPageToken"]
    except KeyError:
        next_page_token = None
    if next_page_token is None:
        return decision

    # Continue, we have a nextPageToken. Assemble a full array of events by continually polling
    all_events = decision["events"]
    while next_page_token is not None:
        try:
            next_page_token = decision["nextPageToken"]
            if next_page_token is not None:
                decision = client.poll_for_decision_task(
                    domain=domain,
                    taskList={"name": task_list},
                    identity=identity,
                    nextPageToken=next_page_token,
                    maximumPageSize=maximum_page_size,
                )
                for event in decision["events"]:
                    all_events.append(event)
        except KeyError:
            next_page_token = None

    # Finally, reset the original decision response with the full set of events
    decision["events"] = all_events

    return decision


def get_input(decision):
    """
    From the decision response, which is JSON data form SWF, get the
    input data that started the workflow
    """
    try:
        workflow_input = json.loads(
            decision["events"][0]["workflowExecutionStartedEventAttributes"]["input"]
        )
    except KeyError:
        workflow_input = None
    return workflow_input


def get_task_token(decision):
    """
    Given a response from polling for decision from SWF via boto,
    extract the taskToken from the json data, if present
    """
    try:
        return decision["taskToken"]
    except KeyError:
        # No taskToken returned
        return None


def get_workflow_type(decision):
    """
    Given a polling for decision response from SWF via boto,
    extract the workflowType from the json data
    """
    try:
        return decision["workflowType"]["name"]
    except KeyError:
        # No workflowType found
        return None


def get_workflow_name(workflow_type):
    """
    Given a workflowType workflow_type, return the name of a
    corresponding workflow class to load
    """
    return "workflow_" + workflow_type


def import_workflow_class(workflow_name):
    """
    Given an workflow subclass name as workflow_name,
    attempt to lazy load the class when needed
    """
    try:
        module_name = "workflow." + workflow_name
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def get_workflow_object(
    workflow_name, settings, logger, client, token, decision, maximum_page_size
):
    """
    Given a workflow_name, and if the module class is already
    imported, create an object an return it
    """
    module_name = "workflow." + workflow_name
    module_object = importlib.import_module(module_name)
    workflow_class = getattr(module_object, workflow_name)
    # Create the object
    workflow_object = workflow_class(
        settings, logger, client, token, decision, maximum_page_size
    )
    return workflow_object


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    process.monitor_interrupt(lambda flag: decide(SETTINGS, flag))
