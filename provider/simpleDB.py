import calendar
import time
from operator import itemgetter

import boto.sdb

import boto.s3
from boto.s3.connection import S3Connection
from provider import utils

"""
SimpleDB S3 data provider
A home for SimpleDB functions so code is not duplicated
"""

class SimpleDB(object):

    def __init__(self, settings):
        self.settings = settings

        self.domain_names = {}
        domain_postfix = ""
        if self.settings.simpledb_domain_postfix:
            domain_postfix = self.settings.simpledb_domain_postfix
        # Set the names of domains = tables in SimpleDB for our data provider
        self.domain_names['S3File'] = "S3File" + domain_postfix
        self.domain_names['S3FileLog'] = "S3FileLog" + domain_postfix

        # Actual domain connections (boto objects), save them for future use once gotten
        self.domains = {}

        self.sdb_conn = None

    def connect(self):
        if self.settings.simpledb_region:
            region = self.settings.simpledb_region
        else:
            region = "us-east-1"
        self.sdb_conn = self.connect_to_sdb(region, self.settings.aws_access_key_id,
                                            self.settings.aws_secret_access_key)
        return self.sdb_conn

    def get_item(self, domain_name, item_name, consistent_read=True):
        """
        Encapsulate boto.sdb get_item, by additionally specifying the domain to read from
        """
        try:
            self.is_domain(domain_name)
        except:
            pass

        dom = self.domains[domain_name]
        return dom.get_item(item_name, consistent_read)

    def put_attributes(self, domain_name, item_name, item_attrs):
        """
        Encapsulate boto.sdb put_attributes, by additionally specifying the domain to put into
        """
        try:
            self.is_domain(domain_name)
        except:
            pass

        dom = self.domains[domain_name]
        dom.put_attributes(item_name, item_attrs)

    def is_domain(self, domain_name):
        """
        Given a domain name, check if the domain is connected,
        and if not, connect to it
        """
        try:
            if not self.domains[domain_name]:
                self.sdb_get_domain(domain_name)
        except KeyError:
            self.sdb_get_domain(domain_name)

    def get_domain_name(self, domain_name):
        """
        Given a domain identifier, return the name of the domain (table)
        used at SimpleDB for the particular settings environment
        """
        try:
            return self.domain_names[domain_name]
        except IndexError:
            return None

    def get_domain(self, domain_name):
        """
        Given a domain name, return the domain
        """
        domain = None
        try:
            self.is_domain(domain_name)
        except:
            pass

        try:
            domain = self.domains[domain_name]
        except:
            pass

        return domain

    def connect_to_sdb(self, region="us-east-1",
                       aws_access_key_id=None, aws_secret_access_key=None):
        return boto.sdb.connect_to_region(region, aws_access_key_id=aws_access_key_id,
                                          aws_secret_access_key=aws_secret_access_key)

    def sdb_domain_exists(self, domain_name_env):
        exists = None
        try:
            dom = self.sdb_conn.get_domain(domain_name_env, validate=True)
            if dom:
                exists = True
        except boto.exception.SDBResponseError:
            exists = False
        return exists

    def sdb_create_domain(self, domain_name_env):
        dom = self.sdb_conn.create_domain(domain_name_env)
        return dom

    def sdb_get_domain(self, domain_name, auto_create_domain=True):
        """
        Get the SimpleDB domain, and optionally create it if is does not yet exist
        """

        # Actual domain name is specific to the environment by adding a prefix
        domain_name_env = self.domain_names[domain_name]

        dom = None
        try:
            dom = self.sdb_conn.get_domain(domain_name_env)
        except boto.exception.SDBResponseError:
            # Domain did not exist, create if we specified to
            if auto_create_domain:
                if self.sdb_domain_exists(domain_name_env) is False:
                    dom = self.sdb_create_domain(domain_name_env)
            else:
                dom = None

        # Add the domain so we can use it again later
        self.domains[domain_name] = dom

        return dom

    def escape(self, val):
        """
        Escape single apostrophe with double apostrophe
        for strings used in SimpleDB queries
        """
        if val:
            val = str(val).replace("'", "''")
        return val

    def elife_get_POA_delivery_S3_file_items(self, last_updated_since=None):
        """
        From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
            last_updated_since:       only return items updated since the date provided
        """
        bucket_name = self.settings.poa_bucket
        return self.elife_get_generic_delivery_S3_file_items(bucket_name, last_updated_since)

    def elife_get_production_final_delivery_S3_file_items(self, last_updated_since=None):
        """
        From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
            last_updated_since:       only return items updated since the date provided
        """
        bucket_name = self.settings.publishing_buckets_prefix + self.settings.production_bucket
        return self.elife_get_generic_delivery_S3_file_items(bucket_name, last_updated_since)

    def elife_get_lens_jpg_S3_file_items(self, last_updated_since=None):
        """
        From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
            last_updated_since:       only return items updated since the date provided
        """
        bucket_name = self.settings.lens_jpg_bucket
        return self.elife_get_generic_delivery_S3_file_items(bucket_name, last_updated_since)

    def elife_get_generic_delivery_S3_file_items(self, bucket_name, last_updated_since=None):
        """
        From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
            last_updated_since:       only return items updated since the date provided
        """

        domain_name = "S3FileLog"

        item_list = []

        domain_name_env = self.get_domain_name(domain_name)
        query = self.elife_get_generic_delivery_S3_query(utils.DATE_TIME_FORMAT, domain_name_env,
                                                         bucket_name, last_updated_since)

        dom = self.get_domain(domain_name)

        rs = dom.select(query)
        for j in rs:
            item_list.append(j)

        return item_list

    def elife_get_generic_delivery_S3_query(self, date_format, domain_name,
                                            bucket_name=None, last_updated_since=None):
        """
        Build a query for SimpleDB to get S3 poa_bucket bucket data
        from the S3FileLog domain, for example
        """

        query = ""

        # Assemble where clause
        where_clause = ""
        where_delimiter = " where"

        # Constrain to the specified bucket
        if bucket_name:
            where_clause += where_delimiter + " bucket_name = '" + bucket_name + "'"
            where_delimiter = " and"

        last_updated_since_present = False

        if last_updated_since:
            # Select based on timestamp
            date_str = time.strptime(last_updated_since, date_format)
            timestamp = calendar.timegm(date_str)
            if timestamp:
                where_clause += (where_delimiter + " last_modified_timestamp > '" +
                                 str(timestamp) + "'")
                where_delimiter = " and"
                last_updated_since_present = True

        # Add a name clause if none was added, or AWS complains about the orderby
        if last_updated_since_present is False:
            where_clause += where_delimiter + " last_modified_timestamp is not null"

        order_by = " order by last_modified_timestamp desc"

        # Assemble the query
        query = 'select * from ' + domain_name + ''
        query = query + where_clause
        query = query + order_by

        return query
