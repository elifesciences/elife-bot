import calendar
import datetime
import time
import importlib
from collections import OrderedDict

from pytz import timezone

import log
import provider.swfmeta as swfmetalib
from provider import utils

"""
SWF cron
"""

TIMEZONE = timezone("Europe/London")


IDENTITY = log.identity("cron")
LOGGER = log.logger("cron.log", "INFO", IDENTITY)


def run_cron(settings):
    current_datetime = utils.get_current_datetime()
    LOGGER.info("current_datetime: %s" % current_datetime)

    for conditional_start in conditional_starts(current_datetime):
        do_start = workflow_conditional_start(
            settings=settings,
            workflow_id=conditional_start.get("workflow_id"),
            start_seconds=conditional_start.get("start_seconds"),
        )
        if do_start:
            LOGGER.info(
                "starting %s, workflow_id %s"
                % (
                    conditional_start.get("starter_name"),
                    conditional_start.get("workflow_id"),
                )
            )
            start_workflow(
                settings=settings,
                starter_name=conditional_start.get("starter_name"),
                workflow_id=conditional_start.get("workflow_id"),
            )


def get_local_datetime(current_datetime, timezone_object):
    """apply the timezone delta to the datetime and remove the tzinfo"""
    new_current_datetime = current_datetime

    # create new datetime with no timezone prior to localize call
    current_datetime_without_tz = datetime.datetime(
        current_datetime.year,
        current_datetime.month,
        current_datetime.day,
        current_datetime.hour,
        current_datetime.minute,
        current_datetime.second,
    )
    localized_current_datetime = timezone_object.localize(
        current_datetime_without_tz, is_dst=False
    )

    if localized_current_datetime.utcoffset():
        new_current_datetime = current_datetime + localized_current_datetime.utcoffset()
        new_current_datetime = new_current_datetime.replace(tzinfo=None)

    return new_current_datetime


def conditional_starts(current_datetime):
    """given the current time in UTC, return a list of workflows for conditional start"""
    conditional_start_list = []

    current_time = current_datetime.utctimetuple()

    # localised time
    local_current_datetime = get_local_datetime(current_datetime, TIMEZONE)
    local_current_time = local_current_datetime.utctimetuple()

    # Based on the minutes of the current time, run certain starters
    if current_time.tm_min >= 0 and current_time.tm_min <= 59:
        # Jobs to start at any time during the hour

        conditional_start_list.append(
            OrderedDict(
                [
                    ("starter_name", "cron_FiveMinute"),
                    ("workflow_id", "cron_FiveMinute"),
                    ("start_seconds", 60 * 3),
                ]
            )
        )

        conditional_start_list.append(
            OrderedDict(
                [
                    ("starter_name", "starter_DepositCrossref"),
                    ("workflow_id", "DepositCrossref"),
                    ("start_seconds", 60 * 3),
                ]
            )
        )

    # Based on the minutes of the current time, run certain starters
    if current_time.tm_min >= 0 and current_time.tm_min <= 14:
        # Jobs to start at the top of the hour
        LOGGER.info("Top of the hour")

        # POA Publish at specific hours of the day UK time
        if local_current_time.tm_hour in (10, 12, 14, 16):
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PublishPOA"),
                        ("workflow_id", "PublishPOA"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # CLOCKSS deposits once per day 22:00 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_CLOCKSS"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # CNKI deposits once per day 23:00 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_CNKI"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

    elif current_time.tm_min >= 15 and current_time.tm_min <= 19:
        # Jobs to start at quarter past the hour
        LOGGER.info("Quarter past the hour")

        conditional_start_list.append(
            OrderedDict(
                [
                    ("starter_name", "starter_DepositCrossrefPendingPublication"),
                    ("workflow_id", "DepositCrossrefPendingPublication"),
                    ("start_seconds", 60 * 31),
                ]
            )
        )

        # Zendy deposits once per day 21:15 UTC
        if current_time.tm_hour == 21:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_Zendy"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # OVID deposits once per day 22:15 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_OVID"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # Scilit deposits once per day 23:15 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_Scilit"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

    elif current_time.tm_min >= 20 and current_time.tm_min <= 29:
        # Jobs to start at 20 minutes past the hour
        LOGGER.info("Twenty minutes past the hour")

        # POA Packaging at UK local time, run between 6:20 and 15:30
        if local_current_time.tm_hour >= 6 and local_current_time.tm_hour <= 15:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "cron_NewS3POA"),
                        ("workflow_id", "cron_NewS3POA"),
                        ("start_seconds", 60 * 3),
                    ]
                )
            )

        if current_time.tm_min >= 25 and current_time.tm_min <= 29:
            # Check for new docmaps and preprints at 25 minutes past the hour
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_FindNewDocmaps"),
                        ("workflow_id", "FindNewDocmaps"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

    elif current_time.tm_min >= 30 and current_time.tm_min <= 44:
        # Jobs to start at the half past to quarter to the hour
        LOGGER.info("half past to quarter to the hour")

        # POA Packaging at UK local time, run between 6:20 and 15:30
        if local_current_time.tm_hour >= 6 and local_current_time.tm_hour <= 15:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "cron_NewS3POA"),
                        ("workflow_id", "cron_NewS3POA"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # PMC deposits once per day 20:30 UTC
        if current_time.tm_hour == 20:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_PMC"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # Web of Science deposits once per day 21:30 UTC
        if current_time.tm_hour == 21:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_WoS"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # OA Switchboard deposits once per day 22:30 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_OASwitchboard"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # CNPIEC deposits once per day 23:30 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_CNPIEC"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

    elif current_time.tm_min >= 45 and current_time.tm_min <= 59:
        # Bottom quarter of the hour

        # Find Preprint PDFs once per day 00:45 UTC
        if current_time.tm_hour == 0:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_FindReadyToFinishPreprints"),
                        ("workflow_id", "FindReadyToFinishPreprints"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # Pub router deposits once per day 23:45 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_HEFCE"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # Cengage deposits once per day 22:45 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_Cengage"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # Author emails at 22:45 local time
        if local_current_time.tm_hour == 22:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PublicationEmail"),
                        ("workflow_id", "PublicationEmail"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        # GoOA / CAS deposits once per day 21:45 UTC
        if current_time.tm_hour == 21:
            conditional_start_list.append(
                OrderedDict(
                    [
                        ("starter_name", "starter_PubRouterDeposit"),
                        ("workflow_id", "PubRouterDeposit_GoOA"),
                        ("start_seconds", 60 * 31),
                    ]
                )
            )

        conditional_start_list.append(
            OrderedDict(
                [
                    ("starter_name", "starter_PubmedArticleDeposit"),
                    ("workflow_id", "PubmedArticleDeposit"),
                    ("start_seconds", 60 * 31),
                ]
            )
        )

        conditional_start_list.append(
            OrderedDict(
                [
                    ("starter_name", "starter_AdminEmail"),
                    ("workflow_id", "AdminEmail"),
                    ("start_seconds", (60 * 60 * 4) - (14 * 60)),
                ]
            )
        )

    return conditional_start_list


def workflow_conditional_start(
    settings, start_seconds, workflow_id=None, workflow_name=None, workflow_version=None
):
    """
    Given workflow criteria, check the workflow completion history for the last time run
    If it last run more than start_seconds ago, start a new workflow
    """

    diff_seconds = None
    last_startTimestamp = None

    swfmeta = swfmetalib.SWFMeta(settings)
    swfmeta.connect()

    last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
    )

    current_timestamp = calendar.timegm(time.gmtime())

    if last_startTimestamp is not None:
        diff_seconds = current_timestamp - start_seconds - last_startTimestamp

    if diff_seconds >= 0 or last_startTimestamp is None:
        return True
    LOGGER.info(
        "workflow name %s, id %s, ran previously at %s, %s seconds short to start again"
        % (workflow_name, workflow_id, last_startTimestamp, diff_seconds)
    )


def start_workflow(settings, starter_name, workflow_id=None):
    """start the workflow using the starter"""
    # Start a new workflow
    # Load the starter module
    module_name = "starter." + starter_name
    module_object = importlib.import_module(module_name)
    starter_class = getattr(module_object, starter_name)
    starter_object = starter_class()

    # Customised start functions
    if starter_name == "starter_AdminEmail":
        starter_object.start(settings=settings)

    elif starter_name == "starter_PubRouterDeposit":
        # PubRouterDeposit has different variants specified by the workflow variable
        workflow = workflow_id.split("_")[-1]
        starter_object.start(settings=settings, workflow=workflow)

    elif starter_name in [
        "cron_FiveMinute",
        "starter_PublishPOA",
        "cron_NewS3POA",
        "starter_PublicationEmail",
        "starter_DepositCrossref",
        "starter_DepositCrossrefPeerReview",
        "starter_DepositCrossrefPendingPublication",
        "starter_PubmedArticleDeposit",
        "starter_FindNewDocmaps",
        "starter_FindReadyToFinishPreprints",
    ]:
        starter_object.start(settings=settings)


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    run_cron(settings=SETTINGS)
