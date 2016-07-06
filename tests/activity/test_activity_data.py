import json
import classes_mock

json_output_parameter_example_string = open("tests/test_data/ConvertJATS_json_output_for_add_update_date_to_json.json", "r").read()
json_output_parameter_example = json.loads(open("tests/test_data/ConvertJATS_json_output_for_add_update_date_to_json.json", "r").read())
json_output_return_example = json.loads(open("tests/test_data/ConvertJATS_add_update_date_to_json_return.json", "r").read())
json_output_return_example_string = open("tests/test_data/ConvertJATS_add_update_date_to_json_return.json", "r").read()

xml_content_for_xml_key = open("tests/test_data/ConvertJATS_content_for_test_origin.xml", "r").read()

bucket_origin_file_name = "test_origin.xml"
bucket_dest_file_name = "test_dest.json"

session_example = {
            'version': '1',
            'article_id': '00353',
            'run': '1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
            'expanded_folder': '00353.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
            'update_date': '2012-12-13T00:00:00Z',
        }
key_names = [u'00353.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda/elife-00353-fig1-v1.tif', u'00353.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda/elife-00353-v1.pdf',
             u'00353.1/1ee54f9a-cb28-4c8e-8232-4b317cf4beda/elife-00353-v1.xml']

bucket = {
    bucket_origin_file_name: xml_content_for_xml_key,
    bucket_dest_file_name: ""
}

run_example = '1ee54f9a-cb28-4c8e-8232-4b317cf4beda'


def PostEIFBridge_data(published):
        return {
                'eif_filename': '00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251/elife-00353-v1.json',
                'eif_bucket':  'jen-elife-publishing-eif',
                'article_id': u'00353',
                'version': u'1',
                'run': u'cf9c7e86-7355-4bb4-b48e-0bc284221251',
                'article_path': 'content/1/e00353v1',
                'published': published,
                'expanded_folder': u'00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251',
                'status': u'vor',
                'update_date': u'2012-12-13T00:00:00Z'
            }
PostEIFBridge_test_dir = "fake_sqs_queue_container"
PostEIFBridge_message = {'workflow_name': 'PostPerfectPublication', 'workflow_data': {'status': u'vor', 'update_date': u'2012-12-13T00:00:00Z', 'run': u'cf9c7e86-7355-4bb4-b48e-0bc284221251', 'expanded_folder': u'00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251', 'version': u'1', 'eif_location': '00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251/elife-00353-v1.json', 'article_id': u'00353'}}


# ExpandArticle

ExpandArticle_data = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-vor-v1-20121213000000.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}
ExpandArticle_data1 = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-v1-20121213000000.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}
ExpandArticle_filename = 'elife-00353-vor-v1-20121213000000.zip'
ExpandArticle_path = 'elife-00353-vor-v1'
ExpandArticle_files_source_folder = 'tests/files_source'
ExpandArticle_files_dest_folder = 'tests/files_dest'
ExpandArticle_files_dest_expected = ['elife-00353-fig1-v1.tif', 'elife-00353-v1.pdf', 'elife-00353-v1.xml']
ExpandArticle_files_dest_bytes_expected = [{'name': 'elife-00353-fig1-v1.tif', 'bytes': 961324}, {'name': 'elife-00353-v1.pdf', 'bytes': 936318}, {'name': 'elife-00353-v1.xml', 'bytes': 9458}]

ExpandArticle_data_invalid_article = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'aaa.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}
ExpandArticle_data_invalid_version = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-vor-v-1-20121213000000.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}

ExpandArticle_data_invalid_status1 = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-v1.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}
ExpandArticle_data_invalid_status2 = {u'event_time': u'2016-06-07T10:45:18.141126Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-v1-20121213000000.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}

#ResizeImages

ResizeImages_data = {u'event_time': u'2016-06-14T12:32:38.084176Z', u'event_name': u'ObjectCreated:Put', u'file_name': u'elife-00353-vor-v1-20121213000000.zip', u'file_etag': u'1e17ebb1fad6c467fce9cede16bb752f', u'bucket_name': u'jen-elife-production-final', u'file_size': 1097506}