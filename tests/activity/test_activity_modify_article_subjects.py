import unittest
from io import StringIO
from collections import OrderedDict
from ddt import ddt, data, unpack
import settings_mock
from activity.activity_ModifyArticleSubjects import activity_ModifyArticleSubjects
from mock import mock, patch
import test_activity_data as test_data
from classes_mock import FakeLogger
from classes_mock import FakeSession
from classes_mock import FakeStorageContext
import shutil
import os
import helpers

session_example = {
            'version': '1',
            'article_id': '29353',
            'run': '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
            'expanded_folder': 'modify_article_subjects'
        }

test_csv_data = u'''DOI,subj-group-type,subject
10.7554/eLife.29353,heading,Subject 1
10.7554/eLife.29353,heading,Subject 2, and more
10.7554/eLife.99999,heading,Subject 1
'''




@ddt
class TestModifyArticleSubjects(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        self.activity = activity_ModifyArticleSubjects(settings_mock, self.logger, None, None, None)
        self.test_files_dir_name = 'tests/files_source/modify_article_subjects/'

    def tearDown(self):
        self.clean_directories()

    def clean_directories(self):
        self.activity.clean_tmp_dir()
        helpers.delete_files_in_folder('tests/tmp', filter_out=['.keepme'])
        #helpers.delete_files_in_folder(test_data.ExpandArticle_files_dest_folder)

    @patch('activity.activity_ModifyArticleSubjects.storage_context')
    @patch.object(activity_ModifyArticleSubjects, 'emit_monitor_event')
    @patch('activity.activity_ModifyArticleSubjects.get_session')
    @patch.object(FakeStorageContext, 'list_resources')
    def test_do_activity(self, fake_list_resources, fake_session, fake_emit_monitor_event,
                         fake_storage_context):
        "test do_activity"
        fake_session.return_value = FakeSession(session_example)
        fake_storage_context.return_value = FakeStorageContext()
        fake_list_resources.return_value = [os.path.join(self.test_files_dir_name,  'elife-29353-v1.xml')]
        result = self.activity.do_activity(test_data.ExpandArticle_data)
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)


    def test_parse_subjects_file(self):
        "test parsing the csv data"
        csv_file = StringIO(test_csv_data)
        subjects_data = self.activity.parse_subjects_file(csv_file)
        expected = [
            OrderedDict([
                ('DOI', '10.7554/eLife.29353'),
                ('subject_group_type', 'heading'),
                ('subject', 'Subject 1')
                ]),
            OrderedDict([
                ('DOI', '10.7554/eLife.29353'),
                ('subject_group_type', 'heading'),
                ('subject', 'Subject 2, and more')
                ]),
            OrderedDict([
                ('DOI', '10.7554/eLife.99999'),
                ('subject_group_type', 'heading'),
                ('subject', 'Subject 1')
                ])
            ]
        self.assertEqual(subjects_data, expected)


    def test_subjects_by_doi(self):
        csv_file = StringIO(test_csv_data)
        doi = '10.7554/eLife.29353'
        subjects_data = self.activity.parse_subjects_file(csv_file)
        subjects_data_by_doi = self.activity.subjects_by_doi(subjects_data, doi)
        expected = [
            OrderedDict([
                ('DOI', '10.7554/eLife.29353'),
                ('subject_group_type', 'heading'),
                ('subject', 'Subject 1')
                ]),
            OrderedDict([
                ('DOI', '10.7554/eLife.29353'),
                ('subject_group_type', 'heading'),
                ('subject', 'Subject 2, and more')
                ])
            ]
        self.assertEqual(subjects_data_by_doi, expected)


    @data(
        # empty data
        (None, None, None),
        )
    @unpack
    def test_subjects_by_doi_bad_data(self, subjects_data, doi, expected):
        subjects_data_by_doi = self.activity.subjects_by_doi(subjects_data, doi)
        self.assertEqual(subjects_data_by_doi, expected)


    @patch.object(activity_ModifyArticleSubjects, 'data_settings')
    @data(
        (None, None, None),
        ('bucket', None, None),
        (None, 'file_name', None)
        )
    @unpack
    def test_load_subjects_data_bad_data(self, data_bucket_name, data_file_name,
                                expected, fake_data_settings):
        "test when settings are incomplete"
        fake_data_settings.return_value = (data_bucket_name, data_file_name)
        subjects_data = self.activity.load_subjects_data()
        self.assertEqual(subjects_data, expected)


    @patch('activity.activity_ModifyArticleSubjects.storage_context')
    @patch.object(FakeStorageContext, 'list_resources')
    @data(
        # test good data
        {
            "resources": ['elife-29353-v1.xml'],
            "expanded_bucket_name": 'bucket',
            "expanded_folder_name": 'modify_article_subjects',
            "expected": 'elife-29353-v1.xml'
        },
        # test for missing XML file
        {
            "resources": [],
            "expanded_bucket_name": 'bucket',
            "expanded_folder_name": 'modify_article_subjects',
            "expected": False
        },
        # test for no bucket settings
        {
            "resources": [],
            "expanded_bucket_name": None,
            "expanded_folder_name": None,
            "expected": False
        },
        )
    def test_download_article_xml(self, test_data, fake_list_resources, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        fake_list_resources.return_value = test_data.get('resources')
        result = self.activity.download_article_xml(
            expanded_bucket_name = test_data.get('expanded_bucket_name'),
            expanded_folder_name = test_data.get('expanded_folder_name'))
        result_file_name = result
        if result:
            # strip the directory name from the result to compare the result
            result_file_name = result.split(os.sep)[-1]
        self.assertEqual(result_file_name, test_data.get('expected'))


    def test_article_doi(self):
        xml_file_name = os.path.join(self.test_files_dir_name, 'elife-29353-v1.xml')
        file_name = xml_file_name.split('/')[-1]
        shutil.copy(xml_file_name, os.path.join(self.activity.get_tmp_dir(), file_name))
        expected = '10.7554/eLife.29353'
        doi = self.activity.article_doi(xml_file_name)
        self.assertEqual(doi, expected)


    def test_data_settings(self):
        "test for when no settings are provided"
        expected = ('bucket_name/modify_article_subjects',
                    'article_subjects.csv')
        self.assertEqual(self.activity.data_settings(), expected)


    def test_data_settings_no_settings(self):
        "test for when no settings are provided"
        self.activity.settings = None
        expected = (None, None)
        self.assertEqual(self.activity.data_settings(), expected)


    @patch('activity.activity_ModifyArticleSubjects.storage_context')
    def test_download_subjects_file(self, fake_storage_context):
        "test downloading the data file"
        fake_storage_context.return_value = FakeStorageContext()
        data_bucket_name = 'bucket_name/modify_article_subjects'
        data_file_name = 'article_subjects.csv'
        expected = os.path.join(self.activity.get_tmp_dir(), data_file_name)
        self.assertEqual(self.activity.download_subjects_file(
            data_bucket_name, data_file_name), expected)


    def test_download_subjects_file_no_settings(self):
        "test if there is no data bucket or file name"
        data_bucket_name = None
        data_file_name = None
        expected = None
        self.assertEqual(self.activity.download_subjects_file(
            data_bucket_name, data_file_name), expected)


    @data(
        # empty data
        (OrderedDict(), False),
        # incomplete values
        (OrderedDict([
            ('DOI', '')
        ]), False),
        # blank subject_group_type
        (OrderedDict([
            ('DOI', '10.7554/eLife.29353'),
            ('subject_group_type', None),
            ('subject', 'Subject 2, and more')
        ]), False),
        # blank subject
        (OrderedDict([
            ('DOI', '10.7554/eLife.29353'),
            ('subject_group_type', 'heading'),
            ('subject', '      ')
        ]), False),
        # complete values
        (OrderedDict([
            ('DOI', '10.7554/eLife.29353'),
            ('subject_group_type', 'heading'),
            ('subject', 'Subject 2, and more')
        ]), True),
        )
    @unpack
    def test_validate_subject(self, subject, expected):
        "test for missing or incomplete subject data"
        self.assertEqual(self.activity.validate_subject(subject), expected)


    def test_create_subjects_map(self):
        csv_file = StringIO(test_csv_data)
        doi = '10.7554/eLife.29353'
        subjects_data = self.activity.parse_subjects_file(csv_file)
        expected = OrderedDict([
            ('heading', [
                'Subject 1',
                'Subject 2, and more'])
            ])
        self.assertEqual(self.activity.create_subjects_map(subjects_data, doi), expected)


    def test_create_subjects_map_bad_data(self):
        "test when validate_subject() encounters incomplete subject_group_type data"
        csv_file = StringIO(test_csv_data)
        doi = '10.7554/eLife.29353'
        subjects_data = [OrderedDict([
            ('DOI', '10.7554/eLife.29353'),
            ('subject_group_type', ''),
            ('subject', 'Subject')
            ])]
        expected = OrderedDict()
        self.assertEqual(self.activity.create_subjects_map(subjects_data, doi), expected)


    @data(
        # successful rewriting of heading subjects
        ('elife-29353-v1.xml',
         OrderedDict([
            ('heading', [
                'Subject 1',
                'Subject 2, and more'])
            ]),
         2,
         'modify_article_subjects_snippet_01.xml'
        ),
        )
    @unpack
    def test_modify_article_subjects(self, xml_file_name, subjects_map,
                                     expected_total, expected_snippet_file):
        "test rewriting the XML file"
        # copy the XML file in
        article_xml_file = os.path.join(self.activity.get_tmp_dir(), xml_file_name)
        shutil.copy(os.path.join(self.test_files_dir_name, xml_file_name),
                    article_xml_file)
        # do the rewrite
        total = self.activity.modify_article_subjects(article_xml_file, subjects_map)
        # check the total
        self.assertEqual(total, expected_total)
        # check the XML file content
        with open(article_xml_file) as open_file:
            file_content = open_file.read()
            print file_content
            # see if the expected snippet of content is in the rewritten XML
            with open(os.path.join(self.test_files_dir_name, expected_snippet_file)) as snippet_file:
                snippet_content = snippet_file.read()
                self.assertTrue(snippet_content in file_content,
                                '{snippet_content} not found in {article_xml_file}'.format(
                                    snippet_content=snippet_content,
                                    article_xml_file=article_xml_file)
                                )
        # clean up
        self.clean_directories()


    @patch('activity.activity_ModifyArticleSubjects.storage_context')
    def test_upload_file_to_bucket(self, fake_storage_context):
        fake_storage_context.return_value = FakeStorageContext()
        xml_file_name = 'elife-29353-v1.xml'
        data_bucket_name = 'bucket_name/modify_article_subjects'
        # copy the file to the folder first
        article_xml_file = os.path.join(self.activity.get_tmp_dir(), xml_file_name)
        shutil.copy(os.path.join(self.test_files_dir_name, xml_file_name),
                    article_xml_file)
        # run the upload
        self.activity.upload_file_to_bucket(data_bucket_name, article_xml_file)
        # check the result
        files = sorted(os.listdir(test_data.ExpandArticle_files_dest_folder))
        self.assertTrue(xml_file_name in files,
                        '{xml_file_name} not found in the destination directory'.format(
                            xml_file_name=xml_file_name)
                       )
        # clean up
        self.clean_directories()


if __name__ == '__main__':
    unittest.main()
