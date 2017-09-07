import os
import shutil
import dateutil.parser
from elifetools import xmlio
from provider import utils

"""
Functions for processing article zip and XML for reuse by different activities
Originally refactoring them from the PMCDeposit activity for reuse into FTPArticle
"""

def list_dir(dir_name):
    dir_list = os.listdir(dir_name)
    dir_list = map(lambda item: dir_name + os.sep + item, dir_list)
    return dir_list

def file_list(dir_name):
    dir_list = list_dir(dir_name)
    return filter(lambda item: os.path.isfile(item), dir_list)


def rename_files_remove_version_number(files_dir, output_dir, logger=None):
    """
    Rename files to not include the version number, if present
    Pre-PPP files will not have a version number, for before PPP is launched
    """

    file_name_map = {}

    # Get a list of all files
    dirfiles = file_list(files_dir)

    for df in dirfiles:
        filename = df.split(os.sep)[-1]

        # Get the new file name
        file_name_map[filename] = None

        # TODO strip the -v1 from it
        file_extension = filename.split('.')[-1]
        if '-v' in filename:
            # Use part before the -v number
            part_without_version = filename.split('-v')[0]
        else:
            # No -v found, use the file name minus the extension
            part_without_version = ''.join(filename.split('.')[0:-1])

        renamed_filename = part_without_version + '.' + file_extension

        if renamed_filename:
            file_name_map[filename] = renamed_filename
        else:
            if logger:
                logger.info('there is no renamed file for ' + filename)

    for old_name, new_name in file_name_map.iteritems():
        if new_name is not None:
            shutil.move(files_dir + os.sep + old_name, output_dir + os.sep + new_name)

    return file_name_map


def convert_xml(xml_file, file_name_map):

    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict = xmlio.parse(xml_file, return_doctype_dict=True)

    # Convert xlink href values
    total = xmlio.convert_xlink_href(root, file_name_map)
    # TODO - compare whether all file names were converted

    # Start the file output
    reparsed_string = xmlio.output(root, type=None, doctype_dict=doctype_dict)

    f = open(xml_file, 'wb')
    f.write(reparsed_string)
    f.close()


def verify_rename_files(file_name_map):
    """
    Each file name as key should have a non None value as its value
    otherwise the file did not get renamed to something new and the
    rename file process was not complete
    """
    verified = True
    renamed_list = []
    not_renamed_list = []
    for k, v in file_name_map.items():
        if v is None:
            verified = False
            not_renamed_list.append(k)
        else:
            renamed_list.append(k)

    return (verified, renamed_list, not_renamed_list)


def new_pmc_zip_filename(journal, volume, fid, revision=None):
    filename = journal
    filename = filename + '-' + utils.pad_volume(volume)
    filename = filename + '-' + utils.pad_msid(fid)
    if revision:
        filename = filename + '.r' + str(revision)
    filename += '.zip'
    return filename


def latest_archive_zip_revision(doi_id, s3_keys, journal, status):
    """
    Get the most recent version of the article zip file from the
    list of bucket key names
    """
    s3_key_name = None

    name_prefix_to_match = (journal + '-' + utils.pad_msid(doi_id)
                            + '-' + status + '-v')

    highest = 0
    for key in s3_keys:
        if key["name"].startswith(name_prefix_to_match):
            version_and_date = None
            try:
                parts = key["name"].split(name_prefix_to_match)
                version = parts[1].split('-')[0]
                date_formatted = dateutil.parser.parse(key["last_modified"])
                date_part = date_formatted.strftime('%Y%m%d%H%M%S')
                version_and_date = int(version + date_part)
            except:
                pass
            if version_and_date and version_and_date > highest:
                s3_key_name = key["name"]
                highest = version_and_date

    return s3_key_name


if __name__ == '__main__':
    main()
