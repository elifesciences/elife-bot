import boto.swf
import json
import random
import datetime
import calendar
import time
import requests
import os
import codecs

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.templates as templatelib
import provider.article as articlelib

import provider.filesystem as fslib

"""
LensArticle activity
"""

class activity_LensArticle(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "LensArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*5
        self.description = "Create a lens article index.html page for the particular article."
        
        # Create the filesystem provider
        self.fs = fslib.Filesystem(self.get_tmp_dir())
        
        # Templates provider
        self.templates = templatelib.Templates(settings, self.get_tmp_dir())
        
        # article data provider
        self.article = articlelib.article(settings, self.get_tmp_dir())
        
        # Default templates directory
        self.from_dir = "template"
        
        # CDN bucket
        self.cdn_bucket = settings.publishing_buckets_prefix + settings.ppp_cdn_bucket

    def do_activity(self, data = None):
        """
        Do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        elife_id = None
        # Support for both the starter method and the PostPerfectPublication method
        if data and "data" in data:
            elife_id = data["data"]["elife_id"]
        elif data and "article_id" in data:
            elife_id = data["article_id"]
        
        article_xml_filename = self.article.download_article_xml_from_s3(doi_id = elife_id)
        
        if not article_xml_filename:
            if(self.logger):
                self.logger.info('LensArticle article xml file not found for %s' % str(elife_id))
            return True
        
        self.article.parse_article_file(self.get_tmp_dir() + os.sep + article_xml_filename)
        
        # Check for PoA, we will not create lens article for
        if self.article.is_poa:
            if(self.logger):
                self.logger.info('LensArticle %s is PoA, not creating a lens page' % str(elife_id))
            return True
        
        article_s3key = self.get_article_s3key(elife_id)
        
        filename = "index.html"
        
        article_html = self.get_article_html(from_dir = self.from_dir,
                                             article = self.article,
                                             cdn_bucket = self.cdn_bucket,
                                             article_xml_filename = article_xml_filename)
        
        # Write the document to disk first
        filename_plus_path = self.write_html_file(article_html, filename)
        
        # Now, set the S3 object to the contents of the filename
        # Connect to S3
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        # Lookup bucket
        bucket_name = self.settings.lens_bucket
        bucket = s3_conn.lookup(bucket_name)
        s3key = boto.s3.key.Key(bucket)
        s3key.key = article_s3key
        s3key.set_contents_from_filename(filename_plus_path, replace=True)
        
        if(self.logger):
            self.logger.info('LensArticle created for: %s' % article_s3key)

        return True
    
    def get_article_s3key(self, elife_id):
        """
        Given an eLife article DOI ID (5 digits) assemble the
        S3 key name for where to save the article index.html page
        """
        article_s3key = "/" + str(elife_id).zfill(5) + "/index.html"
        
        return article_s3key
        
    def get_article_html(self, from_dir, article, cdn_bucket, article_xml_filename):
        """
        Given the URL of the article XML file, create a lens article index.html page
        using header, footer or template, as required
        """
        
        if(from_dir is None):
            from_dir = self.from_dir
            
        print article_xml_filename
        article_html = self.templates.get_lens_article_html(from_dir,
                                                            article,
                                                            cdn_bucket,
                                                            article_xml_filename)

        return article_html
        
    def write_html_file(self, article_html, filename):
        """
        Write the HTML to the disk
        """
        
        filename_plus_path = self.get_tmp_dir() + os.sep + filename
        mode = "w"
        f = codecs.open(filename_plus_path, mode, encoding='utf8')
        f.write(article_html)
        f.close()
        
        return filename_plus_path