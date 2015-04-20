import os
import boto.swf
import json
import random
import datetime
import importlib
import calendar
import time
import arrow

import zipfile
import requests
import urlparse
import glob
import shutil
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib
import provider.article as articlelib
import provider.s3lib as s3lib

"""
PubRouterDeposit activity
"""

class activity_PubRouterDeposit(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PubRouterDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = ("Download article XML from pub_router outbox, \
                            approve each for publication, and deposit files via FTP to pub router.")
        
        # Create output directories
        self.date_stamp = self.set_datestamp()
        
        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)
        
        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())
        
        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = None
        self.published_folder = None
        
        # Track the success of some steps
        self.activity_status = None
        self.ftp_status = None
        self.outbox_status = None
        self.publish_status = None
        
        self.outbox_s3_key_names = None
        
        # Type of FTPArticle workflow to start, will be specified in data
        self.workflow = None
        
        # Track XML files selected
        self.article_xml_filenames = []
        self.xml_file_to_doi_map = {}
        self.articles = []

        #self.article_published_file_names = []
        #self.article_not_published_file_names = []
        
        self.admin_email_content = ''
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        self.workflow = data["data"]["workflow"]
        self.outbox_folder = self.get_outbox_folder(self.workflow)
        self.published_folder = self.get_published_folder(self.workflow)
        
        if self.outbox_folder is None or self.published_folder is None:
            # Total fail
            return False
        
        # Download the S3 objects from the outbox
        self.article_xml_filenames = self.download_files_from_s3_outbox()
        # Parse the XML
        self.articles = self.parse_article_xml(self.article_xml_filenames)
        # Approve the articles to be sent
        self.articles_approved = self.approve_articles(self.articles, self.workflow)
      
      
        for article in self.articles_approved:
            # Start a workflow for each article this is approved to publish
            starter_status = self.start_ftp_article_workflow(article)
            
            if starter_status is True:
                if(self.logger):
                    log_info = "Started an FTPArticle workflow for article: " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
            else:
                if(self.logger):
                    log_info = "FAILED to start an FTPArticle workflow for article: " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                

        # Clean up outbox
        print "Moving files from outbox folder to published folder"
        self.clean_outbox()
        self.outbox_status = True
        
        # Send email to admins with the status
        self.activity_status = True
        self.send_admin_email()

        # Return the activity result, True or False
        result = True

        return result

    def get_outbox_folder(self, workflow):
        """
        S3 outbox, where files to be processed are
        """
        if workflow == "HEFCE":
            return "pub_router/outbox/"
        elif workflow == "Cengage":
            return "cengage/outbox/"
        
        return None
        
    def get_published_folder(self, workflow):
        """
        S3 published folder, where processed files are copied to
        """
        if workflow == "HEFCE":
            return "pub_router/published/"
        elif workflow == "Cengage":
            return "cengage/published/"
        
        return None
        
    def start_ftp_article_workflow(self, article):
        """
        In here a new FTPArticle workflow is started for the article object supplied
        """
        starter_status = None
        
        # Compile the workflow starter parameters
        workflow_id = "FTPArticle_" + self.workflow + "_" + str(article.doi_id)
        workflow_name = "FTPArticle"
        workflow_version = "1"
        child_policy = None
        # Allow workflow 120 minutes to finish
        execution_start_to_close_timeout = str(60*120)
        
        # Input data
        data = {}
        data['workflow'] = self.workflow
        data['elife_id'] = article.doi_id
        input_json = {}
        input_json['data'] = data
        input = json.dumps(input_json)
        
        # Connect to SWF
        conn = boto.swf.layer1.Layer1(self.settings.aws_access_key_id,
                                      self.settings.aws_secret_access_key)
        
        # Try and start a workflow
        try:
            response = conn.start_workflow_execution(self.settings.domain, workflow_id,
                                                     workflow_name, workflow_version,
                                                     self.settings.default_task_list,
                                                     child_policy,
                                                     execution_start_to_close_timeout, input)
            starter_status = True
        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            print message
            if(self.logger):
                self.logger.info(message)
            starter_status = False
        
        return starter_status

    def set_datestamp(self):
        a = arrow.utcnow()
        date_stamp = str(a.datetime.year) + str(a.datetime.month).zfill(2) + str(a.datetime.day).zfill(2)
        return date_stamp

    def download_files_from_s3_outbox(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml to be processed
        """
        filenames = []
        
        file_extensions = []
        file_extensions.append(".xml")
        
        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = self.outbox_folder,
            file_extensions = file_extensions)
        
        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)
  
            filename = name.split("/")[-1]
            
            # Download to the activity temp directory
            dirname = self.get_tmp_dir()
  
            filename_plus_path = dirname + os.sep + filename
            
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()
            
            filenames.append(filename_plus_path)
            
        return filenames
            
    def parse_article_xml(self, article_xml_filenames):
      """
      Given a list of article XML filenames,
      parse the files and add the article object to our article map
      """
      
      articles = []
      
      for article_xml_filename in article_xml_filenames:
    
        article = self.create_article()
        article.parse_article_file(article_xml_filename)
        if(self.logger):
          log_info = "Parsed " + article.doi_url
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
        # Add article object to the object list
        articles.append(article)
  
        # Add article to the DOI to file name map
        self.xml_file_to_doi_map[article.doi] = article_xml_filename
      
      return articles

    def create_article(self, doi_id = None):
      """
      Instantiate an article object and optionally populate it with
      data for the doi_id (int) supplied
      """
      
      # Instantiate a new article object
      article = articlelib.article(self.settings, self.get_tmp_dir())
      
      if doi_id:
        # Get and parse the article XML for data
        # Convert the doi_id to 5 digit string in case it was an integer
        if type(doi_id) == int:
          doi_id = str(doi_id).zfill(5)
        article_xml_filename = article.download_article_xml_from_s3(doi_id)
        article.parse_article_file(self.get_tmp_dir() + os.sep + article_xml_filename)
      return article

    def approve_articles(self, articles, workflow):
      """
      Given a list of article objects, approve them for processing    
      """
      
      approved_articles = []
          
      # Keep track of which articles to remove at the end
      remove_article_doi = []
      
      # Create a blank article object to use its functions
      blank_article = self.create_article()
      # Remove based on published status
      
      for article in articles:
        # Article object knows if it is POA or not
        is_poa = article.is_poa
        # Need to check S3 for whether the DOI was ever POA
        #  using the blank article object to hopefully make only one S3 connection
        was_ever_poa = blank_article.check_was_ever_poa(article.doi)
        
        # Set the value on the article object for later, it is useful
        article.was_ever_poa = was_ever_poa
        
        # Now can check if published
        is_published = blank_article.check_is_article_published(article.doi, is_poa, was_ever_poa)
        if is_published is not True:
          if(self.logger):
            log_info = "Removing because it is not published " + article.doi
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
          remove_article_doi.append(article.doi)
      
      # Check if article is a resupply
      # TODO !!!  Probably to check the published bucket history

      # Check if article is on the blacklist to not send again
      for article in articles:
        blacklisted = self.is_article_on_blacklist(article.doi_id, workflow)
        if blacklisted is True:
          if(self.logger):
            log_info = "Removing because it is blacklisted from sending again to pub router " + article.doi
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
          remove_article_doi.append(article.doi)
      
      # Can remove the articles now without affecting the loops using del
      for article in articles:
        if article.doi not in remove_article_doi:
          approved_articles.append(article)
  
      return approved_articles
    
    def get_filename_from_path(self, f, extension):
        """
        Get a filename minus the supplied file extension
        and without any folder or path
        """
        filename = f.split(extension)[0]
        # Remove path if present
        try:
            filename = filename.split(os.sep)[-1]
        except:
            pass
        
        return filename
        
    def get_to_folder_name(self):
        """
        From the date_stamp
        return the S3 folder name to save published files into
        """
        to_folder = None
        
        date_folder_name = self.date_stamp
        to_folder = self.published_folder + date_folder_name + "/"

        return to_folder
    
    def clean_outbox(self):
      """
      Clean out the S3 outbox folder
      """
      
      to_folder = self.get_to_folder_name()
      
      # Move only the published files from the S3 outbox to the published folder
      bucket_name = self.publish_bucket
      
      # Connect to S3 and bucket
      s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
      bucket = s3_conn.lookup(bucket_name)
      
      # Concatenate the expected S3 outbox file names
      s3_key_names = []
      
      # Compile a list of the published file names
      remove_doi_list = []
      processed_file_names = []
      for article in self.articles_approved:
        remove_doi_list.append(article.doi)
          
      for k, v in self.xml_file_to_doi_map.items():
        if k in remove_doi_list:
          processed_file_names.append(v)
      
      for name in processed_file_names:
          filename = name.split(os.sep)[-1]
          s3_key_name = self.outbox_folder + filename
          s3_key_names.append(s3_key_name)
      
      for name in s3_key_names:
          # Download objects from S3 and save to disk
  
          # Do not delete the from_folder itself, if it is in the list
          if name != self.outbox_folder:
              filename = name.split("/")[-1]
              new_s3_key_name = to_folder + filename
              
              # First copy
              new_s3_key = None
              try:
                  new_s3_key = bucket.copy_key(new_s3_key_name, bucket_name, name)
              except:
                  pass
              
              # Then delete the old key if successful
              if(isinstance(new_s3_key, boto.s3.key.Key)):
                  old_s3_key = bucket.get_key(name)
                  old_s3_key.delete()
        
    def is_article_on_blacklist(self, doi_id, workflow):
        """
        Check if article is on the do not send email list
        This is used to not send a publication email when an article is correct
        For articles published prior to the launch of this publication email feature
          we cannot check the log of all emails sent to check if a duplicate
          email exists already
        """
        
        # Convert to string for matching
        if type(doi_id) == int:
          doi_id = str(doi_id).zfill(5)
        
        if doi_id in self.get_article_blacklist(workflow):
          return True      
        else:
          return False
        
    def get_article_blacklist(self, workflow):
        """
        Return list of do not send article DOI id
        """
      
        if workflow == "HEFCE":
            article_blacklist = [
            "00003", "00005", "00007", "00011", "00013", "00031", "00047", "00048", "00049", "00051", 
            "00065", "00067", "00068", "00070", "00078", "00090", "00093", "00102", "00109", "00117", 
            "00171", "00173", "00181", "00184", "00205", "00240", "00242", "00243", "00248", "00270", 
            "00281", "00286", "00301", "00302", "00311", "00326", "00340", "00347", "00351", "00352", 
            "00353", "00365", "00385", "00386", "00387", "00475", "00012", "00036", "00105", "00116", 
            "00133", "00160", "00170", "00178", "00183", "00190", "00218", "00220", "00230", "00231", 
            "00247", "00260", "00269", "00278", "00288", "00290", "00291", "00299", "00306", "00308", 
            "00312", "00321", "00324", "00327", "00329", "00333", "00334", "00336", "00337", "00348", 
            "00354", "00358", "00362", "00367", "00378", "00380", "00400", "00411", "00415", "00421", 
            "00422", "00425", "00426", "00429", "00435", "00444", "00450", "00452", "00458", "00459", 
            "00461", "00467", "00471", "00473", "00476", "00477", "00481", "00482", "00488", "00491", 
            "00498", "00499", "00505", "00508", "00515", "00518", "00522", "00523", "00533", "00534", 
            "00537", "00542", "00558", "00563", "00565", "00569", "00571", "00572", "00573", "00577", 
            "00592", "00593", "00594", "00603", "00605", "00615", "00625", "00626", "00631", "00632", 
            "00633", "00638", "00639", "00640", "00641", "00642", "00646", "00647", "00648", "00654", 
            "00655", "00658", "00659", "00663", "00666", "00668", "00669", "00672", "00675", "00676", 
            "00683", "00691", "00692", "00699", "00704", "00708", "00710", "00712", "00723", "00726", 
            "00729", "00731", "00736", "00744", "00745", "00747", "00750", "00757", "00759", "00762", 
            "00767", "00768", "00772", "00776", "00778", "00780", "00782", "00785", "00790", "00791", 
            "00792", "00799", "00800", "00801", "00802", "00804", "00806", "00808", "00813", "00822", 
            "00824", "00825", "00828", "00842", "00844", "00845", "00855", "00856", "00857", "00861", 
            "00862", "00863", "00866", "00868", "00873", "00882", "00884", "00886", "00895", "00899", 
            "00903", "00905", "00914", "00924", "00926", "00932", "00933", "00940", "00943", "00947", 
            "00948", "00951", "00953", "00954", "00958", "00960", "00961", "00963", "00966", "00967", 
            "00969", "00971", "00983", "00992", "00994", "00996", "00999", "01004", "01008", "01009", 
            "01020", "01029", "01030", "01042", "01045", "01061", "01064", "01067", "01071", "01074", 
            "01084", "01085", "01086", "01089", "01096", "01098", "01102", "01104", "01108", "01114", 
            "01115", "01119", "01120", "01123", "01127", "01133", "01135", "01136", "01138", "01139", 
            "01140", "01149", "01157", "01159", "01160", "01169", "01179", "01180", "01197", "01202", 
            "01206", "01211", "01213", "01214", "01221", "01222", "01228", "01229", "01233", "01234", 
            "01236", "01252", "01256", "01270", "01273", "01279", "01287", "01289", "01291", "01293", 
            "01294", "01295", "01296", "01298", "01299", "01305", "01312", "01319", "01323", "01326", 
            "01328", "01339", "01340", "01341", "01345", "01350", "01387", "01388", "01402", "01403", 
            "01414", "01426", "01428", "01456", "01462", "01469", "01482", "01494", "01501", "01503", 
            "01514", "01515", "01516", "01519", "01541", "01557", "01561", "01574", "01587", "01597", 
            "01599", "01605", "01608", "01633", "01658", "01662", "01663", "01680", "01700", "01710", 
            "01738", "01749", "01760", "01779", "01809", "01816", "01820", "01839", "01845", "01873", 
            "01893", "01926", "01968", "01979", "02094", "00590", "00662", "00829", "01201", "01239", 
            "01257", "01267", "01308", "01310", "01311", "01322", "01355", "01369", "01370", "01374", 
            "01381", "01385", "01386", "01412", "01433", "01434", "01438", "01439", "01440", "01457", 
            "01460", "01465", "01473", "01479", "01481", "01483", "01488", "01489", "01496", "01498", 
            "01524", "01530", "01535", "01539", "01566", "01567", "01569", "01579", "01581", "01584", 
            "01596", "01603", "01604", "01607", "01610", "01612", "01621", "01623", "01630", "01632", 
            "01637", "01641", "01659", "01671", "01681", "01684", "01694", "01695", "01699", "01715", 
            "01724", "01730", "01739", "01741", "01751", "01754", "01763", "01775", "01776", "01808", 
            "01812", "01817", "01828", "01831", "01832", "01833", "01834", "01846", "01849", "01856", 
            "01857", "01861", "01867", "01879", "01883", "01888", "01892", "01901", "01906", "01911", 
            "01913", "01914", "01916", "01917", "01928", "01936", "01939", "01944", "01948", "01949", 
            "01958", "01963", "01964", "01967", "01977", "01982", "01990", "01993", "01998", "02001", 
            "02008", "02009", "02020", "02024", "02025", "02028", "02030", "02040", "02041", "02042", 
            "02043", "02046", "02053", "02057", "02061", "02062", "02069", "02076", "02077", "02078", 
            "02087", "02088", "02104", "02105", "02109", "02112", "02115", "02130", "02131", "02137", 
            "02148", "02151", "02152", "02164", "02171", "02172", "02181", "02184", "02189", "02190", 
            "02196", "02199", "02200", "02203", "02206", "02208", "02217", "02218", "02224", "02230", 
            "02236", "02238", "02242", "02245", "02252", "02257", "02260", "02265", "02270", "02272", 
            "02273", "02277", "02283", "02286", "02289", "02304", "02313", "02322", "02324", "02349", 
            "02362", "02365", "02369", "02370", "02372", "02375", "02384", "02386", "02387", "02391", 
            "02394", "02395", "02397", "02403", "02407", "02409", "02419", "02439", "02440", "02443", 
            "02444", "02445", "02450", "02451", "02475", "02478", "02481", "02482", "02490", "02501", 
            "02504", "02510", "02511", "02515", "02516", "02517", "02523", "02525", "02531", "02535", 
            "02536", "02555", "02557", "02559", "02564", "02565", "02576", "02583", "02589", "02590", 
            "02598", "02615", "02618", "02619", "02626", "02630", "02634", "02637", "02641", "02653", 
            "02658", "02663", "02667", "02669", "02670", "02671", "02674", "02676", "02678", "02687", 
            "02715", "02725", "02726", "02730", "02734", "02736", "02740", "02743", "02747", "02750", 
            "02755", "02758", "02763", "02772", "02777", "02780", "02784", "02786", "02791", "02792", 
            "02798", "02805", "02809", "02811", "02812", "02813", "02833", "02839", "02840", "02844", 
            "02848", "02851", "02854", "02860", "02862", "02863", "02866", "02869", "02872", "02875", 
            "02882", "02893", "02897", "02904", "02907", "02910", "02917", "02923", "02935", "02938", 
            "02945", "02949", "02950", "02951", "02956", "02963", "02964", "02975", "02978", "02981", 
            "02993", "02996", "02999", "03005", "03007", "03011", "03023", "03025", "03031", "03032", 
            "03035", "03043", "03058", "03061", "03068", "03069", "03075", "03077", "03080", "03083", 
            "03091", "03100", "03104", "03110", "03115", "03116", "03125", "03126", "03128", "03145", 
            "03146", "03159", "03164", "03176", "03178", "03180", "03185", "03191", "03197", "03198", 
            "03205", "03206", "03222", "03229", "03233", "03235", "03239", "03245", "03251", "03254", 
            "03255", "03271", "03273", "03275", "03282", "03285", "03293", "03297", "03300", "03307", 
            "03311", "03318", "03342", "03346", "03348", "03351", "03357", "03363", "03371", "03372", 
            "03374", "03375", "03383", "03385", "03397", "03398", "03399", "03401", "03405", "03406", 
            "03416", "03421", "03422", "03427", "03430", "03433", "03435", "03440", "03443", "03445", 
            "03464", "03467", "03468", "03473", "03475", "03476", "03487", "03496", "03497", "03498", 
            "03502", "03504", "03521", "03522", "03523", "03526", "03528", "03532", "03542", "03545", 
            "03549", "03553", "03558", "03563", "03564", "03568", "03573", "03574", "03575", "03579", 
            "03581", "03582", "03583", "03587", "03596", "03600", "03602", "03604", "03606", "03609", 
            "03613", "03626", "03635", "03638", "03640", "03641", "03648", "03650", "03653", "03656", 
            "03658", "03663", "03665", "03671", "03674", "03676", "03678", "03679", "03680", "03683", 
            "03695", "03696", "03697", "03701", "03702", "03703", "03706", "03711", "03714", "03720", 
            "03722", "03724", "03726", "03727", "03728", "03735", "03737", "03743", "03751", "03753", 
            "03754", "03756", "03764", "03765", "03766", "03772", "03778", "03779", "03781", "03785", 
            "03790", "03804", "03811", "03819", "03821", "03830", "03842", "03848", "03851", "03868", 
            "03881", "03883", "03891", "03892", "03895", "03896", "03908", "03915", "03925", "03939", 
            "03941", "03943", "03949", "03952", "03962", "03970", "03971", "03977", "03978", "03980", 
            "03981", "03997", "04000", "04006", "04008", "04014", "04024", "04034", "04037", "04040", 
            "04046", "04047", "04057", "04059", "04066", "04069", "04070", "04094", "04105", "04106", 
            "04111", "04114", "04120", "04121", "04123", "04126", "04132", "04135", "04137", "04147", 
            "04158", "04165", "04168", "04177", "04180", "04187", "04193", "04205", "04207", "04220", 
            "04234", "04235", "04236", "04246", "04247", "04249", "04251", "04263", "04265", "04266", 
            "04273", "04279", "04287", "04288", "04300", "04316", "04333", "04353", "04363", "04366", 
            "04371", "04378", "04380", "04387", "04389", "04390", "04395", "04402", "04406", "04407", 
            "04415", "04418", "04433", "04437", "04449", "04476", "04478", "04489", "04491", "04494", 
            "04499", "04501", "04506", "04517", "04525", "04530", "04531", "04534", "04543", "04551", 
            "04553", "04563", "04565", "04577", "04580", "04581", "04586", "04591", "04600", "04601", 
            "04603", "04605", "04617", "04629", "04630", "04631", "04645", "04660", "04664", "04686", 
            "04692", "04693", "04711", "04729", "04741", "04742", "04766", "04775", "04779", "04785", 
            "04801", "04806", "04811", "04851", "04854", "04869", "04875", "04876", "04878", "04885", 
            "04889", "04901", "04902", "04909", "04919", "04969", "04970", "04986", "04995", "04996", 
            "04997", "04998", "05000", "05007", "05025", "05031", "05033", "05041", "05048", "05055", 
            "05060", "05075", "05087", "05105", "05115", "05116", "05125", "05151", "05161", "05169", 
            "05178", "05179", "05198", "05216", "05218", "05244", "05256", "05259", "05269", "05289", 
            "05290", "05334", "05352", "05375", "05377", "05394", "05401", "05418", "05419", "05422", 
            "05427", "05438", "05490", "05504", "05508", "05553", "05558", "05564", "05570", "05580", 
            "05597", "05614", "05657", "05663", "05720", "05770", "05787", "05789", "05816", "05846", 
            "05896", "05983", "06156", "06193", "06200", "06235", "06303", "06306", "06351", "06424", 
            "06430", "06453", "06494", "06656", "06720", "06740", "06900", "06986"]

        elif workflow == "Cengage":
            article_blacklist = [
            "00003", "00005", "00007", "00011", "00012", "00013", "00031", "00036", "00047", 
            "00048", "00049", "00051", "00065", "00067", "00068", "00070", "00078", "00090", 
            "00093", "00102", "00105", "00109", "00116", "00117", "00133", "00160", "00170", 
            "00171", "00173", "00178", "00181", "00183", "00184", "00190", "00205", "00218", 
            "00220", "00230", "00231", "00240", "00242", "00243", "00247", "00248", "00260", 
            "00269", "00270", "00278", "00281", "00286", "00288", "00290", "00291", "00299", 
            "00301", "00302", "00306", "00308", "00311", "00312", "00321", "00324", "00326", 
            "00327", "00329", "00333", "00334", "00336", "00337", "00340", "00347", "00348", 
            "00351", "00352", "00353", "00354", "00358", "00362", "00365", "00367", "00378", 
            "00380", "00385", "00386", "00387", "00400", "00411", "00415", "00421", "00422", 
            "00425", "00426", "00429", "00435", "00444", "00450", "00452", "00458", "00459", 
            "00461", "00467", "00471", "00473", "00475", "00476", "00477", "00481", "00482", 
            "00488", "00491", "00498", "00499", "00505", "00508", "00515", "00518", "00522", 
            "00523", "00533", "00534", "00537", "00542", "00558", "00563", "00565", "00569", 
            "00571", "00572", "00573", "00577", "00590", "00592", "00593", "00594", "00603", 
            "00605", "00615", "00625", "00626", "00631", "00632", "00633", "00638", "00639", 
            "00640", "00641", "00642", "00646", "00647", "00648", "00654", "00655", "00658", 
            "00659", "00662", "00663", "00666", "00668", "00669", "00672", "00675", "00676", 
            "00683", "00691", "00692", "00699", "00704", "00708", "00710", "00712", "00723", 
            "00726", "00729", "00731", "00736", "00744", "00745", "00747", "00750", "00757", 
            "00759", "00762", "00767", "00768", "00772", "00776", "00778", "00780", "00782", 
            "00785", "00790", "00791", "00792", "00799", "00800", "00801", "00802", "00804", 
            "00806", "00808", "00813", "00822", "00824", "00825", "00828", "00829", "00842", 
            "00844", "00845", "00855", "00856", "00857", "00861", "00862", "00863", "00866", 
            "00868", "00873", "00882", "00884", "00886", "00895", "00899", "00903", "00905", 
            "00914", "00924", "00926", "00932", "00933", "00940", "00943", "00947", "00948", 
            "00951", "00953", "00954", "00958", "00960", "00961", "00963", "00966", "00967", 
            "00969", "00971", "00983", "00992", "00994", "00996", "00999", "01004", "01008", 
            "01009", "01020", "01029", "01030", "01042", "01045", "01061", "01064", "01067", 
            "01071", "01074", "01084", "01085", "01086", "01089", "01096", "01098", "01102", 
            "01104", "01108", "01114", "01115", "01119", "01120", "01123", "01127", "01133", 
            "01135", "01136", "01138", "01139", "01140", "01149", "01157", "01159", "01160", 
            "01169", "01179", "01180", "01197", "01201", "01202", "01206", "01211", "01213", 
            "01214", "01221", "01222", "01228", "01229", "01233", "01234", "01236", "01239", 
            "01252", "01256", "01257", "01267", "01270", "01273", "01279", "01287", "01289", 
            "01291", "01293", "01294", "01295", "01296", "01298", "01299", "01305", "01308", 
            "01310", "01311", "01312", "01319", "01322", "01323", "01326", "01328", "01339", 
            "01340", "01341", "01345", "01350", "01355", "01369", "01370", "01374", "01381", 
            "01385", "01386", "01387", "01388", "01402", "01403", "01412", "01414", "01426", 
            "01428", "01433", "01434", "01438", "01439", "01440", "01456", "01457", "01460", 
            "01462", "01465", "01469", "01473", "01479", "01481", "01482", "01483", "01488", 
            "01489", "01494", "01496", "01498", "01501", "01503", "01514", "01515", "01516", 
            "01519", "01524", "01530", "01535", "01539", "01541", "01557", "01561", "01566", 
            "01567", "01569", "01574", "01579", "01581", "01584", "01587", "01596", "01597", 
            "01599", "01603", "01604", "01605", "01607", "01608", "01610", "01612", "01621", 
            "01623", "01630", "01632", "01633", "01637", "01641", "01658", "01659", "01662", 
            "01663", "01671", "01680", "01681", "01684", "01694", "01695", "01699", "01700", 
            "01710", "01715", "01724", "01730", "01738", "01739", "01741", "01749", "01751", 
            "01754", "01760", "01763", "01775", "01776", "01779", "01808", "01809", "01812", 
            "01816", "01817", "01820", "01828", "01831", "01832", "01833", "01834", "01839", 
            "01845", "01846", "01849", "01856", "01857", "01861", "01867", "01873", "01879", 
            "01883", "01888", "01892", "01893", "01901", "01906", "01911", "01913", "01914", 
            "01916", "01917", "01926", "01928", "01936", "01939", "01944", "01948", "01949", 
            "01958", "01963", "01964", "01967", "01968", "01977", "01979", "01982", "01990", 
            "01993", "01998", "02001", "02008", "02009", "02020", "02024", "02025", "02028", 
            "02030", "02040", "02041", "02042", "02043", "02046", "02053", "02057", "02061", 
            "02062", "02069", "02076", "02077", "02078", "02087", "02088", "02094", "02104", 
            "02105", "02109", "02112", "02115", "02130", "02131", "02137", "02148", "02151", 
            "02152", "02164", "02171", "02172", "02181", "02184", "02189", "02190", "02196", 
            "02199", "02200", "02203", "02206", "02208", "02217", "02218", "02224", "02230", 
            "02236", "02238", "02242", "02245", "02252", "02257", "02260", "02265", "02270", 
            "02272", "02273", "02277", "02283", "02286", "02289", "02304", "02313", "02322", 
            "02324", "02349", "02362", "02365", "02369", "02370", "02372", "02375", "02384", 
            "02386", "02387", "02391", "02394", "02395", "02397", "02403", "02407", "02409", 
            "02419", "02439", "02440", "02443", "02444", "02445", "02450", "02451", "02475", 
            "02478", "02481", "02482", "02490", "02501", "02504", "02510", "02511", "02515", 
            "02516", "02517", "02523", "02525", "02531", "02535", "02536", "02555", "02557", 
            "02559", "02564", "02565", "02576", "02583", "02589", "02590", "02598", "02615", 
            "02618", "02619", "02626", "02630", "02634", "02637", "02641", "02653", "02658", 
            "02663", "02667", "02669", "02670", "02671", "02674", "02676", "02678", "02687", 
            "02715", "02725", "02726", "02730", "02734", "02736", "02740", "02743", "02747", 
            "02750", "02755", "02758", "02763", "02772", "02777", "02780", "02784", "02786", 
            "02791", "02792", "02798", "02805", "02809", "02811", "02812", "02813", "02833", 
            "02839", "02840", "02844", "02848", "02851", "02854", "02860", "02862", "02863", 
            "02866", "02869", "02872", "02875", "02882", "02893", "02897", "02904", "02907", 
            "02910", "02917", "02923", "02935", "02938", "02945", "02948", "02949", "02950", 
            "02951", "02956", "02963", "02964", "02975", "02978", "02981", "02993", "02996", 
            "02999", "03005", "03007", "03011", "03023", "03025", "03031", "03032", "03035", 
            "03043", "03058", "03061", "03068", "03069", "03075", "03077", "03080", "03083", 
            "03091", "03100", "03104", "03110", "03115", "03116", "03125", "03126", "03128", 
            "03145", "03146", "03159", "03164", "03176", "03178", "03180", "03185", "03189", 
            "03191", "03197", "03198", "03205", "03206", "03222", "03229", "03233", "03235", 
            "03239", "03245", "03251", "03254", "03255", "03256", "03270", "03271", "03273", 
            "03275", "03282", "03285", "03293", "03297", "03300", "03307", "03311", "03318", 
            "03342", "03346", "03348", "03351", "03357", "03363", "03371", "03372", "03374", 
            "03375", "03383", "03385", "03397", "03398", "03399", "03401", "03405", "03406", 
            "03416", "03421", "03422", "03427", "03430", "03433", "03435", "03440", "03443", 
            "03445", "03464", "03467", "03468", "03473", "03475", "03476", "03487", "03496", 
            "03497", "03498", "03502", "03504", "03521", "03522", "03523", "03526", "03528", 
            "03532", "03542", "03545", "03549", "03553", "03558", "03563", "03564", "03568", 
            "03573", "03574", "03575", "03579", "03581", "03582", "03583", "03587", "03596", 
            "03600", "03602", "03604", "03606", "03609", "03613", "03614", "03626", "03635", 
            "03638", "03640", "03641", "03648", "03650", "03653", "03656", "03658", "03663", 
            "03665", "03671", "03674", "03676", "03678", "03679", "03680", "03683", "03695", 
            "03696", "03697", "03701", "03702", "03703", "03706", "03711", "03714", "03720", 
            "03722", "03724", "03726", "03727", "03728", "03735", "03737", "03743", "03751", 
            "03753", "03754", "03756", "03764", "03765", "03766", "03772", "03778", "03779", 
            "03781", "03785", "03790", "03804", "03811", "03819", "03821", "03830", "03842", 
            "03848", "03851", "03868", "03881", "03883", "03891", "03892", "03895", "03896", 
            "03908", "03915", "03925", "03939", "03941", "03943", "03949", "03952", "03962", 
            "03970", "03971", "03977", "03978", "03980", "03981", "03997", "04000", "04006", 
            "04008", "04014", "04024", "04034", "04037", "04040", "04046", "04047", "04052", 
            "04057", "04059", "04066", "04069", "04070", "04094", "04105", "04106", "04111", 
            "04114", "04120", "04121", "04123", "04126", "04132", "04135", "04137", "04147", 
            "04158", "04165", "04168", "04177", "04180", "04186", "04187", "04193", "04205", 
            "04207", "04220", "04232", "04234", "04235", "04236", "04246", "04247", "04249", 
            "04251", "04260", "04263", "04265", "04266", "04273", "04279", "04287", "04288", 
            "04300", "04316", "04333", "04346", "04353", "04363", "04366", "04371", "04378", 
            "04379", "04380", "04387", "04389", "04390", "04395", "04402", "04406", "04407", 
            "04415", "04418", "04433", "04437", "04449", "04463", "04476", "04478", "04489", 
            "04490", "04491", "04494", "04499", "04501", "04506", "04517", "04525", "04530", 
            "04531", "04534", "04535", "04543", "04550", "04551", "04553", "04563", "04565", 
            "04577", "04580", "04581", "04585", "04586", "04591", "04599", "04600", "04601", 
            "04603", "04605", "04617", "04629", "04630", "04631", "04634", "04645", "04660", 
            "04664", "04686", "04692", "04693", "04711", "04726", "04729", "04741", "04742", 
            "04766", "04775", "04779", "04785", "04790", "04801", "04803", "04806", "04811", 
            "04837", "04851", "04854", "04869", "04871", "04872", "04875", "04876", "04878", 
            "04883", "04885", "04889", "04901", "04902", "04909", "04919", "04940", "04953", 
            "04960", "04969", "04970", "04979", "04986", "04995", "04996", "04997", "04998", 
            "05000", "05003", "05007", "05025", "05031", "05033", "05041", "05042", "05048", 
            "05055", "05060", "05075", "05087", "05098", "05105", "05115", "05116", "05118", 
            "05125", "05151", "05154", "05161", "05165", "05166", "05169", "05178", "05179", 
            "05198", "05216", "05218", "05224", "05242", "05244", "05256", "05259", "05269", 
            "05279", "05289", "05290", "05291", "05334", "05338", "05352", "05375", "05377", 
            "05378", "05394", "05401", "05413", "05418", "05419", "05421", "05422", "05423", 
            "05427", "05438", "05447", "05449", "05457", "05463", "05464", "05472", "05477", 
            "05490", "05491", "05503", "05504", "05508", "05534", "05544", "05553", "05557", 
            "05558", "05560", "05564", "05570", "05580", "05597", "05604", "05606", "05608", 
            "05614", "05635", "05657", "05663", "05701", "05720", "05733", "05770", "05787", 
            "05789", "05808", "05816", "05826", "05835", "05846", "05849", "05861", "05868", 
            "05871", "05875", "05896", "05899", "05959", "05983", "06003", "06024", "06034", 
            "06054", "06068", "06074", "06100", "06132", "06156", "06166", "06179", "06184", 
            "06193", "06200", "06235", "06250", "06303", "06306", "06346", "06351", "06369", 
            "06380", "06400", "06412", "06424", "06430", "06453", "06494", "06536", "06557", 
            "06565", "06633", "06656", "06717", "06720", "06740", "06758", "06782", "06808", 
            "06837", "06877", "06883", "06900", "06956", "06986", "06995", "07074", "07083", 
            "07108", "07157", "07204", "07239", "07322", "07364", "07390", "07431", "07482", 
            "07527", "07532", "07586", "07604"
            ]
    
        return article_blacklist
        
    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """
        # Connect to DB
        db_conn = self.db.connect()
        
        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)
      
        current_time = time.gmtime()
        
        body = self.get_admin_email_body(current_time)
        subject = self.get_admin_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email
        
        recipient_email_list = []
        # Handle multiple recipients, if specified
        if(type(self.settings.ses_poa_recipient_email) == list):
          for email in self.settings.ses_poa_recipient_email:
            recipient_email_list.append(email)
        else:
          recipient_email_list.append(self.settings.ses_poa_recipient_email)
    
        for email in recipient_email_list:
          # Add the email to the email queue
          self.db.elife_add_email_to_email_queue(
            recipient_email = email,
            sender_email = sender_email,
            email_type = "PublicationEmail",
            format = "text",
            subject = subject,
            body = body)
          pass
        
        return True
      
    def get_activity_status_text(self, activity_status):
        """
        Given the activity status boolean, return a human
        readable text version
        """
        if activity_status is True:
            activity_status_text = "Success!"
        else:
            activity_status_text = "FAILED."
            
        return activity_status_text
      
    def get_admin_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)
        
        activity_status_text = self.get_activity_status_text(self.activity_status)
        
        subject = ( self.name + " " + str(self.workflow) + " " + activity_status_text +
                    ", " + datetime_string +
                    ", eLife SWF domain: " + self.settings.domain)
        
        return subject
  
    def get_admin_email_body(self, current_time):
        """
        Format the body of the email
        """
        
        body = ""
        
        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)
        
        activity_status_text = self.get_activity_status_text(self.activity_status)
        
        # Bulk of body
        body += "Workflow type:" + str(self.workflow)
        body += "\n"
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"
        body += "Details:" + "\n"
        body += "\n"
        body += self.admin_email_content + "\n"
        body += "\n"
              
        body += "\n"
        body += "-------------------------------\n"
        body += "SWF workflow details: " + "\n"
        body += "activityId: " + str(self.get_activityId()) + "\n"
        body += "As part of workflowId: " + str(self.get_workflowId()) + "\n"
        body += "As at " + datetime_string + "\n"
        body += "Domain: " + self.settings.domain + "\n"
  
        body += "\n"
        
        body += "\n\nSincerely\n\neLife bot"
  
        return body


