import calendar
import time
import datetime
import importlib
from collections import OrderedDict
from argparse import ArgumentParser

from pytz import timezone

import boto.swf
import boto.s3
from boto.s3.connection import S3Connection

import provider.swfmeta as swfmetalib
import starter

import newrelic.agent

"""
SWF cron
"""

TIMEZONE = timezone("Europe/London")


def run_cron(settings):

    current_datetime = get_current_datetime()

    for conditional_start in conditional_starts(current_datetime):
        do_start = workflow_conditional_start(
            settings=settings,
            workflow_id=conditional_start.get("workflow_id"),
            start_seconds=conditional_start.get("start_seconds")
        )
        if do_start:
            start_workflow(
                settings=settings,
                starter_name=conditional_start.get("starter_name"),
                workflow_id=conditional_start.get("workflow_id")
            )


def get_current_datetime():
    """for easier mocking in tests wrap this call"""
    return datetime.datetime.utcnow()


def get_local_datetime(current_datetime, timezone):
    """apply the timezone delta to the datetime and remove the tzinfo"""
    new_current_datetime = current_datetime

    localized_current_datetime = timezone.localize(current_datetime, is_dst=False)
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

        conditional_start_list.append(OrderedDict([
            ("starter_name", "cron_FiveMinute"),
            ("workflow_id", "cron_FiveMinute"),
            ("start_seconds", 60 * 3)
        ]))

    # Based on the minutes of the current time, run certain starters
    if current_time.tm_min >= 0 and current_time.tm_min <= 29:
        # Jobs to start at the top of the hour
        #print "Top of the hour"

        conditional_start_list.append(OrderedDict([
            ("starter_name", "starter_DepositCrossref"),
            ("workflow_id", "DepositCrossref"),
            ("start_seconds", 60 * 31)
        ]))

        # CNKI deposits once per day 23:00 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_CNKI"),
                ("start_seconds", 60 * 31)
            ]))

    elif current_time.tm_min >= 30 and current_time.tm_min <= 44:
        # Jobs to start at the half past to quarter to the hour
        #print "half past to quarter to the hour"

        # POA Publish once per day 12:30 local time
        #  (used to be set to 11:30 UTC during British Summer Time for 12:30 local UK time)
        if local_current_time.tm_hour == 12:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PublishPOA"),
                ("workflow_id", "PublishPOA"),
                ("start_seconds", 60 * 31)
            ]))

        # POA bucket polling
        conditional_start_list.append(OrderedDict([
            ("starter_name", "starter_S3Monitor"),
            ("workflow_id", "S3Monitor_POA"),
            ("start_seconds", 60 * 31)
        ]))

        # PMC deposits once per day 20:30 UTC
        if current_time.tm_hour == 20:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_PMC"),
                ("start_seconds", 60 * 31)
            ]))

        # Web of Science deposits once per day 21:30 UTC
        if current_time.tm_hour == 21:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_WoS"),
                ("start_seconds", 60 * 31)
            ]))

        # Scopus deposits once per day 22:30 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_Scopus"),
                ("start_seconds", 60 * 31)
            ]))

        # CNPIEC deposits once per day 23:30 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_CNPIEC"),
                ("start_seconds", 60 * 31)
            ]))

    if current_time.tm_min >= 45 and current_time.tm_min <= 59:
        # Bottom quarter of the hour

        # POA Package once per day 11:45 local time
        # (used to be set to 10:45 UTC during British Summer Time for 11:45 local UK time)
        if local_current_time.tm_hour == 11:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "cron_NewS3POA"),
                ("workflow_id", "cron_NewS3POA"),
                ("start_seconds", 60 * 31)
            ]))

        # Author emails once per day 17:45 local time
        # (used to be set to 16:45 UTC during British Summer Time for 17:45 local UK time)
        if current_time.tm_hour == 17:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PublicationEmail"),
                ("workflow_id", "PublicationEmail"),
                ("start_seconds", 60 * 31)
            ]))

        # Pub router deposits once per day 23:45 UTC
        if current_time.tm_hour == 23:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_HEFCE"),
                ("start_seconds", 60 * 31)
            ]))

        # Cengage deposits once per day 22:45 UTC
        if current_time.tm_hour == 22:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_Cengage"),
                ("start_seconds", 60 * 31)
            ]))

        # GoOA / CAS deposits once per day 21:45 UTC
        if current_time.tm_hour == 21:
            conditional_start_list.append(OrderedDict([
                ("starter_name", "starter_PubRouterDeposit"),
                ("workflow_id", "PubRouterDeposit_GoOA"),
                ("start_seconds", 60 * 31)
            ]))

        conditional_start_list.append(OrderedDict([
            ("starter_name", "starter_PubmedArticleDeposit"),
            ("workflow_id", "PubmedArticleDeposit"),
            ("start_seconds", 60 * 31)
        ]))

        conditional_start_list.append(OrderedDict([
            ("starter_name", "starter_AdminEmail"),
            ("workflow_id", "AdminEmail"),
            ("start_seconds", (60*60*4)-(14*60))
        ]))

    return conditional_start_list


def workflow_conditional_start(settings, start_seconds, data=None,
                               workflow_id=None, workflow_name=None, workflow_version=None):
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
        workflow_version=workflow_version)

    current_timestamp = calendar.timegm(time.gmtime())

    if last_startTimestamp is not None:
        diff_seconds = current_timestamp - start_seconds - last_startTimestamp

    if diff_seconds >= 0 or last_startTimestamp is None:
        return True


def start_workflow(settings, starter_name, workflow_id=None):
    """start the workflow using the starter"""
    # Start a new workflow
    # Load the starter module
    module_name = "starter." + starter_name
    importlib.import_module(module_name)
    full_path = "starter." + starter_name + "." + starter_name + "()"
    s = eval(full_path)

    # Customised start functions
    if starter_name == "starter_S3Monitor":

        if workflow_id == "S3Monitor":
            s.start(settings=settings, workflow="S3Monitor")
        if workflow_id == "S3Monitor_POA":
            s.start(settings=settings, workflow="S3Monitor_POA")

    elif starter_name == "starter_AdminEmail":
        s.start(settings=settings, workflow="AdminEmail")

    elif starter_name == "starter_PubmedArticleDeposit":
        # Special for pubmed, only start a workflow if the outbox is not empty
        bucket_name = settings.poa_packaging_bucket
        outbox_folder = "pubmed/outbox/"

        # Connect to S3 and bucket
        s3_conn = S3Connection(settings.aws_access_key_id, settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=outbox_folder
            )
        if len(s3_key_names) > 0:
            s.start(settings=settings)

    elif starter_name == "starter_PubRouterDeposit":
        # PubRouterDeposit has different variants specified by the workflow variable
        workflow = workflow_id.split("_")[-1]
        s.start(settings=settings, workflow=workflow)

    elif (
            starter_name == "cron_FiveMinute"
            or starter_name == "starter_PublishPOA"
            or starter_name == "cron_NewS3POA"
            or starter_name == "starter_PublicationEmail"
            or starter_name == "starter_DepositCrossref"):
        s.start(settings=settings)


def get_s3_key_names_from_bucket(bucket, prefix=None, delimiter='/', headers=None):
    """
    Given a connected boto bucket object, and optional parameters,
    from the prefix (folder name), get the s3 key names for
    non-folder objects, optionally that match a particular
    list of file extensions
    """
    s3_keys = []
    s3_key_names = []

    # Get a list of S3 objects
    bucketList = bucket.list(prefix=prefix, delimiter=delimiter, headers=headers)

    for item in bucketList:
        if isinstance(item, boto.s3.key.Key):
            # Can loop through each prefix and search for objects
            s3_keys.append(item)

    # Convert to key names instead of objects to make it testable later
    for key in s3_keys:
        s3_key_names.append(key.name)

    return s3_key_names


def get_settings(env):
    import settings as settings_lib
    return settings_lib.get_settings(env)


def console_start():
    """capture options when running standalone"""
    parser = ArgumentParser()
    parser.add_argument("-e", "--env", default="dev", action="store", type=str, dest="env",
                        help="set the environment to run, either dev or live")
    args = parser.parse_args()
    if args.env:
        return args.env


if __name__ == "__main__":
    ENV = console_start()
    SETTINGS = get_settings(ENV)
    application = newrelic.agent.register_application(timeout=10.0)
    with newrelic.agent.BackgroundTask(application, name='run_cron', group='cron.py'):
        run_cron(settings=SETTINGS)
