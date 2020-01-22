import boto.swf
import json
import random
import datetime
import calendar
import time
import boto.sdb
import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib
from provider import utils

from activity.objects import Activity

"""
S3Monitor activity
"""

class activity_S3Monitor(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_S3Monitor, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "S3Monitor"
        self.version = "1.1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 20
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 20
        self.description = ("S3Monitor activity: poll S3 bucket and " +
                            "save object metadata into SimpleDB.")

        # Data provider
        self.db = dblib.SimpleDB(settings)

    def do_activity(self, data=None):
        """
        S3Monitor activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        bucket_name = data["data"]["bucket"]
        prefix = self.settings.prefix
        delimiter = self.settings.delimiter

        # Set the current time for this run, to help discover deleted files
        _runtime_timestamp = calendar.timegm(time.gmtime())

        # Connect to DB
        db_conn = self.db.connect()

        # Connect to S3
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)

        # Lookup bucket
        bucket = s3_conn.lookup(bucket_name)

        (keys, folders) = self.get_keys_and_folders(bucket, prefix)

        self.update_keys_and_folder_items(keys, folders, bucket_name,
                                          _runtime_timestamp, prefix, delimiter)

        # Map one more level of directories - a quick hack before parallel execution
        (keys, folders) = self.get_keys_and_folders(bucket, prefix)
        for folder in folders:
            prefix = folder.name
            (keys2, folders2) = self.get_keys_and_folders(bucket, prefix)
            self.update_keys_and_folder_items(keys2, folders2, bucket_name,
                                              _runtime_timestamp, prefix, delimiter)

        return True

    def update_keys_and_folder_items(self, keys, folders, bucket_name,
                                     _runtime_timestamp=None, prefix='', delimiter='/'):
        """
        Given the attributes for keys or folders from S3, update the DB domain
        items with the supplied values. Each attribute of a DB item will be overwritten, not
        appended to a list, in this function.
        Existing attributes for the item are not deleted.
        """

        base_item_attrs = {}
        base_item_attrs['bucket_name'] = bucket_name

        # Logging the activity runtime
        # Get extended _runtime values
        if _runtime_timestamp:
            date_attrs = self.get_expanded_date_attributes(
                base_name='_runtime', date_format=utils.DATE_TIME_FORMAT,
                timestamp=_runtime_timestamp, date_string=None)
            for k, v in list(date_attrs.items()):
                base_item_attrs[k] = v

        for folder in folders:
            # Reset attributes
            item_attrs = base_item_attrs

            item_name = bucket_name + delimiter + folder.name
            #print item_name
            item = self.db.get_item("S3File", item_name, consistent_read=True)

            item_attrs['item_name'] = item_name

            if item is None:
                # Create the item
                self.db.put_attributes("S3File", item_name, item_attrs)
            else:
                # Update the item attributes by replacing values if present
                for k, v in list(item_attrs.items()):
                    if k in item:
                        # Overwrite value
                        item[k] = v
                    else:
                        # Create the new attribute
                        item.add_value(k, v)
                item.save()

        for key in keys:
            # Reset attributes
            item_attrs = base_item_attrs

            item_name = bucket_name + delimiter + key.name
            #print item_name
            item = self.db.get_item("S3File", item_name, consistent_read=True)

            item_attrs['item_name'] = item_name

            # Standard attributes returned from a standard boto list call
            attr_list = ['name', 'content_type', 'etag', 'last_modified',
                         'owner', 'storage_class', 'size']
            # Extended attributes, not used yet
            #  'metadata','cache_control','content_encoding','content_disposition',
            #  'content_language','md5','version_id','encrypted'

            for attr_name in attr_list:
                # Reading values from keys
                #  Ignore None values, but convert others to string first
                #  for simplicity
                raw_value = eval("key." + attr_name)
                if raw_value:
                    string_value = str(raw_value)
                    item_attrs[attr_name] = string_value
                    #print attr_name + ' = ' + item_attrs[attr_name]

            # Get extended last_modified values
            # Example format: 2013-01-26T23:48:28.000Z
            if item_attrs['last_modified']:
                date_attrs = self.get_expanded_date_attributes(
                    base_name='last_modified', date_format=utils.DATE_TIME_FORMAT,
                    timestamp=None, date_string=item_attrs['last_modified'])
                for k, v in list(date_attrs.items()):
                    item_attrs[k] = v

            if item is None:
                # Create the item
                self.db.put_attributes("S3File", item_name, item_attrs)
                # Add to the item log
                self.log_item_modified(item_name, item_attrs)
            else:
                # Log the details if it has been modifed
                if self.item_diff(item, item_name, item_attrs):
                    self.log_item_modified(item_name, item_attrs)

                # Update the item attributes by replacing values if present
                for k, v in list(item_attrs.items()):
                    if k in item:
                        # Overwrite value
                        item[k] = v
                    else:
                        # Create the new attribute
                        item.add_value(k, v)
                item.save()

    def get_expanded_date_attributes(self, base_name='', date_format=utils.DATE_TIME_FORMAT,
                                     timestamp=None, date_string=None):
        """
        Given a base_name as an identifier string, and either a timestamp or a
        date_string value, slice and dice the date into an array of attributes
        to be stored. Timestamp (UNIX seconds, GMT timezone) takes precedence over
        a date string if both are supplied
        """
        date_attrs = {}

        if timestamp is None and date_string is None:
            return None

        if timestamp is None and date_string is not None:
            # Only supplied date_string, parse a timestamp
            date_str = time.strptime(date_string, date_format)
            timestamp = calendar.timegm(date_str)

        time_tuple = time.gmtime(timestamp)

        date_attrs[base_name + '_timestamp'] = timestamp
        date_attrs[base_name + '_date'] = time.strftime(date_format, time_tuple)
        date_attrs[base_name + '_year'] = time.strftime("%Y", time_tuple)
        date_attrs[base_name + '_month'] = time.strftime("%m", time_tuple)
        date_attrs[base_name + '_day'] = time.strftime("%d", time_tuple)
        date_attrs[base_name + '_time'] = time.strftime("%H:%M:%S", time_tuple)

        return date_attrs

    def get_log_item_name(self, item_name, item_attrs):
        """
        Given an item name and its attributes, return what the resulting
        unique log item name would be
        """
        log_item_name = None
        try:
            log_item_name = str(item_attrs['last_modified_timestamp']) + '_' + item_name
        except (KeyError, IndexError):
            log_item_name = '0' + '_' + item_name

        return log_item_name

    def item_diff(self, item, item_name, item_attrs):
        """
        Given an SDB item and some attributes, check for the most recent item
        in the SDB log. If it is unchanged since the last time we looked at it
        return False; if it has changed or the item does not appear in the log,
        return true
        """
        diff = False

        log_item_name = self.get_log_item_name(item_name, item_attrs)

        log_item = self.db.get_item("S3FileLog", log_item_name, consistent_read=True)
        if log_item is None:
            diff = True
        else:
            # Got a log item, compare attributes to determine whether it is modified
            try:
                if(item['item_name'] == log_item['item_name'] and
                   item['last_modified_timestamp'] != item_attrs['last_modified_timestamp']):
                    diff = True
            except KeyError:
                # If last_modified does not exist
                diff = False

        return diff

    def log_item_modified(self, item_name, item_attrs):
        """
        After detecting a new or modified S3 object, add a new item to the
        S3FileLog domain. Each item needs a unique key. If an item already exists
        for the unique key, there's no need to modify it
        """

        domain_name = "S3FileLog"

        log_item_name = self.get_log_item_name(item_name, item_attrs)

        item_attrs['log_item_name'] = log_item_name

        # Check if it already exists
        log_item = self.db.get_item("S3FileLog", log_item_name, consistent_read=True)
        if log_item is None:
            self.db.put_attributes("S3FileLog", log_item_name, item_attrs)


    def get_keys_and_folders(self, bucket, prefix=None, delimiter='/', headers=None):
        # Get "keys" and "folders" from the bucket, with optional
        # prefix for the "folder" of interest
        # default delimiter is '/'

        if bucket is None:
            return None

        folders = []
        keys = []

        bucketList = bucket.list(prefix=prefix, delimiter=delimiter, headers=headers)

        for item in bucketList:
            if isinstance(item, boto.s3.prefix.Prefix):
                # Can loop through each prefix and search for objects
                folders.append(item)
                #print 'Prefix: ' + item.name
            elif isinstance(item, boto.s3.key.Key):
                keys.append(item)
                #print 'Key: ' + item.name

        return keys, folders

