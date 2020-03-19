import json
import os
import csv
from collections import OrderedDict
from elifetools import parseJATS as parser
from provider.storage_provider import storage_context
from provider.execution_context import get_session
from provider.article_structure import ArticleInfo
from elifetools import xmlio
from activity.objects import Activity

"""
ModifyArticleSubjects.py activity
"""

class activity_ModifyArticleSubjects(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ModifyArticleSubjects, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "ModifyArticleSubjects"
        self.pretty_name = "Modify Article Subjects"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Modify subject tags in the article XML file"
        self.logger = logger

        self.total_replacements = None

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            run = data['run']
            session = get_session(self.settings, data, run)
            version = session.get_value('version')
            article_id = session.get_value('article_id')

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start",
                                    "Starting modify article subjects to files for " + article_id)
        except Exception as e:
            self.logger.exception(str(e))
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            expanded_folder_name = session.get_value('expanded_folder')
            expanded_bucket_name = (self.settings.publishing_buckets_prefix
                                    + self.settings.expanded_bucket)

            # main
            article_xml_file = self.download_article_xml(expanded_bucket_name,
                                                         expanded_folder_name)
            if not article_xml_file:
                if self.logger:
                    self.logger.info('unable to download article xml file')
            # parse the doi
            doi = self.article_doi(article_xml_file)
            if not doi:
                if self.logger:
                    self.logger.info('could not parse doi from the article xml')
            # download article subjects data
            subjects_data = self.load_subjects_data()
            # index the subjects by doi
            subjects_data_by_doi = self.subjects_by_doi(subjects_data, doi)
            # rewrite the XML
            self.total_replacements = self.rewrite_xml(article_xml_file, subjects_data_by_doi, doi)
            # upload back to the bucket
            if self.total_replacements and self.total_replacements > 0:
                self.upload_file_to_bucket(expanded_bucket_name, expanded_folder_name, article_xml_file)
            else:
                if self.logger:
                    self.logger.info('did not modify any article subjects in the article xml')

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end",
                                    "Finished modify article subjects to article " + article_id +
                                    " for version " + version + " run " + str(run))

        except Exception as exception:
            self.logger.exception(str(exception))
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error in modify article subjects to files for " + article_id +
                                    " message:" + str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        return self.ACTIVITY_SUCCESS


    def load_subjects_data(self):
        "download and parse the subjects data from the CSV in the bucket"
        subjects_data = None
        data_bucket_name, data_file_name = self.data_settings()
        # log if no subjects data
        if not data_bucket_name:
            if self.logger:
                self.logger.info('no data_bucket_name settings for load_subjects_data')
            return None
        if not data_file_name:
            if self.logger:
                self.logger.info('no data_file_name settings for load_subjects_data')
            return None
        raw_data_file = self.download_subjects_file(data_bucket_name,
                                                    data_file_name)
        if raw_data_file:
            with open(raw_data_file) as csv_file:
                subjects_data = self.parse_subjects_file(csv_file)
        return subjects_data


    def rewrite_xml(self, article_xml_file, subjects_data_by_doi, doi):
        "rewrite the article XML with the subject values"
        total = None
        if subjects_data_by_doi:
            subjects_map = self.create_subjects_map(subjects_data_by_doi, doi)
            total = self.modify_article_subjects(article_xml_file, subjects_map)
        return total


    def download_article_xml(self, expanded_bucket_name, expanded_folder_name):
        "download the article xml from the expanded bucket"
        if not expanded_bucket_name or not expanded_folder_name:
            if self.logger:
                self.logger.info('could not download article xml without bucket settings')
            return None
        bucket_name = expanded_bucket_name
        bucket_folder_name = expanded_folder_name
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + bucket_folder_name
        files_in_bucket = storage.list_resources(orig_resource)
        article_xml_s3_key_name = None
        for filename in files_in_bucket:
            info = ArticleInfo(filename)
            if info.file_type == 'ArticleXML':
                article_xml_s3_key_name = filename
                break
        if not article_xml_s3_key_name:
            if self.logger:
                self.logger.info('article xml file not found in the bucket')
            return None
        # download the file
        article_xml_filename = article_xml_s3_key_name.split('/')[-1]
        filename_plus_path = os.path.join(self.get_tmp_dir(), article_xml_filename)
        with open(filename_plus_path, 'wb') as open_file:
            storage_resource_origin = orig_resource + '/' + article_xml_filename
            storage.get_resource_to_file(storage_resource_origin, open_file)
            return filename_plus_path

    def article_doi(self, xml_filename):
        "parse the doi of the article XML"
        soup = parser.parse_document(xml_filename)
        return parser.doi(soup)

    def data_settings(self):
        "check if there are settings to specify where the article subjects data is stored"
        data_bucket_name = None
        data_file_name = None
        if (hasattr(self.settings, 'article_subjects_data_bucket') and
                hasattr(self.settings, 'article_subjects_data_file')):
            data_bucket_name = self.settings.article_subjects_data_bucket
            data_file_name = self.settings.article_subjects_data_file
        return data_bucket_name, data_file_name

    def download_subjects_file(self, data_bucket_name, data_file_name):
                                                        
        "download the subjects data"
        if not data_bucket_name or not data_file_name:
            return None
        # download and save the file
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + data_bucket_name
        storage_resource_origin = orig_resource + '/' + data_file_name
        filename_plus_path = self.get_tmp_dir() + os.sep + data_file_name
        # check the storage object exists before attempting to download it
        if not storage.resource_exists(storage_resource_origin):
            return None
        with open(filename_plus_path, 'wb') as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        return filename_plus_path

    def parse_subjects_file(self, csv_file):
        "parse the raw data into structured data"
        data_start_row = 1
        subjects_data = []
        csv_reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        # columns: DOI,subject_group_type,subject
        for row in csv_reader:
            # skip header row
            if csv_reader.line_num <= data_start_row:
                continue
            subject = OrderedDict()
            subject['DOI'] = row[0]
            subject['subject_group_type'] = row[1]
            # account for extra commas in the final column
            subject['subject'] = ','.join(row[2:])
            subjects_data.append(subject)
        return subjects_data

    def subjects_by_doi(self, subjects_data, doi):
        "filter the subjects data by doi"
        if not subjects_data or not doi:
            return None
        return [subject for subject in subjects_data if subject.get('DOI') == doi]

    def validate_subject(self, subject_data):
        "check for bad or missing data in a subject"
        non_blank_values = ['DOI', 'subject_group_type', 'subject']
        for value in non_blank_values:
            if (not subject_data.get(value) or
                    subject_data.get(value).strip() == ''):
                return False
        # default
        return True

    def create_subjects_map(self, subjects_data, doi):
        "create a subject_group_type to list of subjects map"
        subjects_map = OrderedDict()
        # filter the data by doi just to be safe
        subjects_data_by_doi = self.subjects_by_doi(subjects_data, doi)
        # compile the map of data
        for subject_data in subjects_data_by_doi:
            # check for missing or malformed data
            if self.validate_subject(subject_data) is False: 
                continue
            subject_group_type = subject_data.get('subject_group_type')
            subject = subject_data.get('subject')
            if subject_group_type not in subjects_map:
                subjects_map[subject_group_type] = []
            # add it to the map
            subjects_map[subject_group_type].append(subject)
        return subjects_map

    def modify_article_subjects(self, article_xml_file, subjects_map):
        """
        Main function to apply the modifications to the article XML file
        """
        total = None
        #filename_plus_path = self.get_tmp_dir() + os.sep + xml_filename
        # download XML, rewrite it and upload it
        for subject_group_type, subjects in list(subjects_map.items()):
            total = self.rewrite_xml_file(article_xml_file, subject_group_type, subjects)
        return total

    def rewrite_xml_file(self, article_xml_file, subject_group_type, subjects):
        xmlio.register_xmlns()

        root, doctype_dict, processing_instructions = xmlio.parse(
            article_xml_file, return_doctype_dict=True, return_processing_instructions=True)

        # Modify subject values
        total = xmlio.rewrite_subject_group(root, subjects, subject_group_type)

        # Start the file output
        reparsed_string = xmlio.output(
            root, type=None, doctype_dict=doctype_dict,
            processing_instructions=processing_instructions)
        with open(article_xml_file, 'wb') as open_file:
            open_file.write(reparsed_string)

        return total

    def upload_file_to_bucket(self, expanded_bucket_name, expanded_folder_name, article_xml_file):
        "upload the XML back to the bucket"
        bucket_name = expanded_bucket_name
        bucket_folder_name = expanded_folder_name
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        file_name_plus_path = article_xml_file
        s3_key_name = file_name_plus_path.split(os.sep)[-1]
        resource_dest = (storage_provider + bucket_name + "/" +
                         bucket_folder_name + "/" + s3_key_name)
        storage.set_resource_from_filename(resource_dest, article_xml_file)
