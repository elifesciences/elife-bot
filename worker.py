import json
import os
import importlib
import boto3
import newrelic.agent
import log
from provider import process, utils
import activity
from activity.objects import Activity


"""
Amazon SWF worker
"""


def work(settings, flag):
    # Log
    identity = "worker_%s" % os.getpid()
    logger = log.logger("worker.log", settings.setLevel, identity)

    # Simple connect
    client = boto3.client(
        "swf",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.swf_region,
    )

    token = None
    application = newrelic.agent.application()

    # Poll for an activity task indefinitely
    while flag.green():
        if token is None:
            logger.info("polling for activity...")
            activity_task = client.poll_for_activity_task(
                domain=settings.domain,
                taskList={"name": settings.default_task_list},
                identity=identity,
            )

            token = get_taskToken(activity_task)

            logger.info(
                "got activity: \n%s",
                json.dumps(activity_task, sort_keys=True, indent=4),
            )

            # Complete the activity based on data and activity type
            activity_result = False
            if token is not None:
                # Get the activityType and attempt to do the work
                activityType = get_activityType(activity_task)
                if activityType is not None:
                    logger.info("activityType: %s", activityType)

                    # Build a string for the object name
                    activity_name = get_activity_name(activityType)

                    with newrelic.agent.BackgroundTask(
                        application, name=activity_name, group="worker.py"
                    ):
                        # Attempt to import the module for the activity
                        if import_activity_class(activity_name):
                            # Instantiate the activity object
                            activity_object = get_activity_object(
                                activity_name,
                                settings,
                                logger,
                                client,
                                token,
                                activity_task,
                            )

                            # Get the data to pass
                            data = get_input(activity_task)

                            # Do the activity
                            try:
                                activity_result = activity_object.do_activity(data)
                            except Exception:
                                logger.error(
                                    "error executing activity %s",
                                    activity_name,
                                    exc_info=True,
                                )

                            # Print the result to the log
                            logger.info(
                                "got result: \n%s",
                                json.dumps(
                                    activity_object.result, sort_keys=True, indent=4
                                ),
                            )

                            # Complete the activity task if it was successful
                            if isinstance(activity_result, str):
                                if activity_result == Activity.ACTIVITY_SUCCESS:
                                    message = activity_object.result
                                    respond_completed(client, logger, token, message)
                                elif (
                                    activity_result
                                    == Activity.ACTIVITY_TEMPORARY_FAILURE
                                ):
                                    reason = (
                                        "error: activity failed with result "
                                        + str(activity_object.result)
                                    )
                                    detail = ""
                                    respond_failed(
                                        client, logger, token, detail, reason
                                    )

                                else:
                                    # (Activity.ACTIVITY_PERMANENT_FAILURE or
                                    #  Activity.ACTIVITY_EXIT_WORKFLOW)
                                    signal_fail_workflow(
                                        client,
                                        logger,
                                        settings.domain,
                                        activity_task["workflowExecution"][
                                            "workflowId"
                                        ],
                                        activity_task["workflowExecution"]["runId"],
                                    )
                            else:
                                # for legacy actions

                                # Complete the activity task if it was successful
                                if activity_result:
                                    message = activity_object.result
                                    respond_completed(client, logger, token, message)
                                else:
                                    reason = (
                                        "error: activity failed with result "
                                        + str(activity_object.result)
                                    )
                                    detail = ""
                                    respond_failed(
                                        client, logger, token, detail, reason
                                    )

                        else:
                            reason = "error: could not load object %s\n" % activity_name
                            detail = ""
                            respond_failed(client, logger, token, detail, reason)
                            logger.info(
                                "error: could not load object %s\n", activity_name
                            )

        # Reset and loop
        token = None

    logger.info("graceful shutdown")


def get_input(activity_task):
    """
    Given a response from polling for activity from SWF via boto,
    extract the input from the json data
    """
    try:
        input_data = json.loads(activity_task["input"])
    except KeyError:
        input_data = None
    return input_data


def get_taskToken(activity_task):
    """
    Given a response from polling for activity from SWF via boto,
    extract the taskToken from the json data, if present
    """
    try:
        return activity_task["taskToken"]
    except KeyError:
        # No taskToken returned
        return None


def get_activityType(activity_task):
    """
    Given a polling for activity response from SWF via boto,
    extract the activityType from the json data
    """
    try:
        return activity_task["activityType"]["name"]
    except KeyError:
        # No activityType found
        return None


def get_activity_name(activityType):
    """
    Given an activityType, return the name of a
    corresponding activity class to load
    """
    return "activity_" + activityType


def activity_module_name(activity_name):
    """
    Given an activity_name, return the name of an
    activity class module
    """
    return "activity." + activity_name


def import_activity_class(activity_name):
    """
    Given an activity subclass name as activity_name,
    attempt to lazy load the class when needed
    """
    try:
        module_name = activity_module_name(activity_name)
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def get_activity_object(activity_name, settings, logger, client, token, activity_task):
    """
    Given an activity_name, and if the module class is already
    imported, create an object an return it
    """
    module_object = importlib.import_module(activity_module_name(activity_name))
    activity_class = getattr(module_object, activity_name)
    # Create the object
    activity_object = activity_class(settings, logger, client, token, activity_task)
    return activity_object


def _log_swf_response_error(logger, exception):
    logger.exception(
        "SWF client exception: status %s, reason %s, body %s",
        exception.status,
        exception.reason,
        exception.body,
    )


def respond_completed(client, logger, token, message):
    """
    Given an SWF client and logger as resources,
    the token to specify an accepted activity and a message
    to send, communicate with SWF that the activity was completed
    """
    try:
        out = client.respond_activity_task_completed(
            taskToken=token, result=str(message)
        )
        logger.info("respond_activity_task_completed returned %s" % out)
    except (
        client.exceptions.OperationNotPermittedFault,
        client.exceptions.UnknownResourceFault,
    ) as exception:
        _log_swf_response_error(logger, exception)


def respond_failed(client, logger, token, details, reason):
    """
    Given an SWF client and logger as resources,
    the token to specify an accepted activity, details and a reason
    to send, communicate with SWF that the activity failed
    """
    try:
        out = client.respond_activity_task_failed(
            taskToken=token, details=str(details), reason=str(reason)
        )
        logger.info("respond_activity_task_failed returned %s" % out)
    except (
        client.exceptions.OperationNotPermittedFault,
        client.exceptions.UnknownResourceFault,
    ) as exception:
        _log_swf_response_error(logger, exception)


def signal_fail_workflow(client, logger, domain, workflow_id, run_id):
    """
    Given an SWF client and logger as resources,
    the token to specify an accepted activity, details and a reason
    to send, communicate with SWF that the activity failed
    and the workflow should be abandoned
    """
    try:
        out = client.request_cancel_workflow_execution(
            domain=domain, workflowId=workflow_id, runId=run_id
        )
        logger.info("request_cancel_workflow_execution %s" % out)
    except (
        client.exceptions.OperationNotPermittedFault,
        client.exceptions.UnknownResourceFault,
    ) as exception:
        _log_swf_response_error(logger, exception)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    process.monitor_interrupt(lambda flag: work(SETTINGS, flag))
