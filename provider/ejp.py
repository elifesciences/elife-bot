import calendar
from operator import itemgetter
import csv
import re
import os
import io
from ejpcsvparser.utils import entity_to_unicode
from provider.storage_provider import storage_context
from provider import utils

"""
EJP data provider
Connects to S3, discovers, downloads, and parses files exported by EJP
"""

# map of CSV file type to file name fragement to match
# For each file_type, specify a unique file name fragment to filter on
#  with regular expression search
S3_FILENAME_FRAGMENT_MAP = {
    "author": r"ejp_query_tool_query_id_15a\)_Accepted_Paper_Details",
    "preprint_author": (
        "ejp_query_tool_query_id_Production_data_04_-_Reviewed_preprint_author_details"
    ),
    "poa_manuscript": "ejp_query_tool_query_id_POA_Manuscript",
    "poa_author": "ejp_query_tool_query_id_POA_Author",
    "poa_license": "ejp_query_tool_query_id_POA_License",
    "poa_subject_area": "ejp_query_tool_query_id_POA_Subject_Area",
    "poa_received": "ejp_query_tool_query_id_POA_Received",
    "poa_research_organism": "ejp_query_tool_query_id_POA_Research_Organism",
    "poa_abstract": "ejp_query_tool_query_id_POA_Abstract",
    "poa_title": "ejp_query_tool_query_id_POA_Title",
    "poa_keywords": "ejp_query_tool_query_id_POA_Keywords",
    "poa_group_authors": "ejp_query_tool_query_id_POA_Group_Authors",
    "poa_datasets": "ejp_query_tool_query_id_POA_Datasets",
    "poa_funding": "ejp_query_tool_query_id_POA_Funding",
    "poa_ethics": "ejp_query_tool_query_id_POA_Ethics",
}


class EJP:
    def __init__(self, settings, tmp_dir):
        self.settings = settings
        self.tmp_dir = tmp_dir

        # Default S3 bucket name
        self.bucket_name = None
        if self.settings is not None:
            self.bucket_name = self.settings.ejp_bucket

        # Some EJP file types we expect
        self.author_default_filename = "authors.csv"

    def write_content_to_file(self, filename, content, mode="wb"):
        "write the content to a file in the tmp_dir"
        document = None
        # set the document path
        try:
            document_path = os.path.join(self.tmp_dir, filename)
        except TypeError:
            document_path = None
        # decide the encoding to use
        encoding = "utf-8"
        if "b" in mode:
            encoding = None
        # write the content to the file
        try:
            with open(document_path, mode, encoding=encoding) as open_file:
                open_file.write(content)
                # success, set the document value to return
                document = document_path
        except (TypeError, IOError):
            document = None
        return document

    def get_authors(self, doi_id=None, corresponding=None):
        """
        Get a list of authors for an article
          If doi_id is None, return all authors
          If corresponding is
            True, return corresponding authors
            False, return all but corresponding authors
            None, return all authors
        """

        # Find the document on S3, save the content to
        #  the tmp_dir
        storage = storage_context(self.settings)
        s3_key_name = self.find_latest_s3_file_name(file_type="author")
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.bucket_name
            + "/"
            + s3_key_name
        )
        contents = storage.get_resource_as_string(s3_resource)
        document = self.write_content_to_file(self.author_default_filename, contents)

        return author_detail_list(document, doi_id, corresponding)

    def get_preprint_authors(self, doi_id, version):
        "get a list of authors for a preprint article"

        # Find the document on S3, save the content to
        #  the tmp_dir
        storage = storage_context(self.settings)
        s3_key_name = self.find_latest_s3_file_name(file_type="preprint_author")
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.bucket_name
            + "/"
            + s3_key_name
        )
        contents = storage.get_resource_as_string(s3_resource)
        document = self.write_content_to_file(self.author_default_filename, contents)

        return preprint_author_detail_list(document, doi_id, version)

    def find_latest_s3_file_name(self, file_type, file_list=None):
        """
        Given the file_type, find the name of the S3 key for the object
        that is the latest file in the S3 bucket
          file_type options: author, editor
        Optional: for running tests, provide a file_list without connecting to S3
        """

        s3_key_name = None

        # first try to locate the s3 key by looking for the expected name
        s3_key_name = self.latest_s3_file_name_by_convention(
            S3_FILENAME_FRAGMENT_MAP, file_type
        )

        if not s3_key_name:
            # find s3_key_name by checking for the latest modified date on the s3 key
            s3_key_name = self.latest_s3_file_name_by_modified_date(
                S3_FILENAME_FRAGMENT_MAP, file_type, file_list
            )

        return s3_key_name

    def latest_s3_file_name_by_convention(self, fn_fragment, file_type):
        "concatenate the expected s3 file name and check if it exists in the bucket"
        date_string = utils.set_datestamp("_")
        # remove backslashes from regular expression fragments
        clean_fn_fragment = fn_fragment[file_type].replace("\\", "")
        # add an extra part of file name for new CSV files
        rp_extra = "eLife"
        if "Reviewed_preprint_author_details" in clean_fn_fragment:
            # note lower case l
            rp_extra = "elife-rp"
        file_name_to_match = "%s_%s_%s.csv" % (
            clean_fn_fragment,
            date_string,
            rp_extra,
        )
        storage = storage_context(self.settings)
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.bucket_name
            + "/"
            + file_name_to_match
        )
        if storage.resource_exists(s3_resource):
            return file_name_to_match
        return None

    def latest_s3_file_name_by_modified_date(self, fn_fragment, file_type, file_list):
        if file_list is None:
            file_list = self.ejp_bucket_file_list()

        if file_list:
            good_file_list = []
            pattern = fn_fragment[file_type]
            # First copy all the good file names over
            for s3_file in file_list:
                if re.search(pattern, s3_file["name"]) is not None:
                    good_file_list.append(s3_file)
            # Second, sort by last_updated_timestamp
            sorted_good_file_list = sorted(
                good_file_list, key=itemgetter("last_modified_timestamp"), reverse=True
            )

            if len(sorted_good_file_list) > 0:
                # We still have a list, take the name of the first one
                s3_key_name = sorted_good_file_list[0]["name"]

        return s3_key_name

    def ejp_bucket_file_list(self):
        """
        Connect to the EJP bucket, as specified in the settings,
        use boto to list all keys in the root of the bucket,
        extract interesting values and collapse into JSON
        so we can test it later
        """
        storage = storage_context(self.settings)
        resource = self.settings.storage_provider + "://" + self.bucket_name + "/"
        # List bucket contents
        keys = storage.list_resources(resource, return_keys=True)

        file_list = []

        for key in keys:
            item_attrs = {}
            item_attrs["name"] = key.get("Key")
            item_attrs["last_modified"] = key.get("LastModified").strftime(
                utils.DATE_TIME_FORMAT
            )
            # Convert last_modified into a timestamp for easy computations
            item_attrs["last_modified_timestamp"] = calendar.timegm(
                key.get("LastModified").timetuple()
            )
            # Finally, add to the file list
            if len(item_attrs) > 0:
                file_list.append(item_attrs)

        if len(file_list) <= 0:
            # Return None if no S3 keys were found
            file_list = None

        return file_list


def author_detail_list(document, doi_id=None, corresponding=None):
    "get author details from the document as a list"

    authors = []

    # Parse the author file
    (column_headings, author_rows) = parse_author_file(document)

    if author_rows:
        for fields in author_rows:
            add = True
            # Check doi_id column value
            if doi_id is not None:
                if int(doi_id) != int(fields[0]):
                    add = False
            # Check corresponding column value
            if corresponding is not None and add is True:
                author_type_cde = fields[4]
                dual_corr_author_ind = fields[5]
                is_corr = is_corresponding_author(author_type_cde, dual_corr_author_ind)
                if corresponding is True:
                    # If not a corresponding author, drop it
                    if is_corr is not True:
                        add = False
                elif corresponding is False:
                    # If is a corresponding author, drop it
                    if is_corr is True:
                        add = False
            fields = [entity_to_unicode(field) for field in fields]
            # Finish up, add the author if we should
            if add is True:
                authors.append(fields)

    if len(authors) <= 0:
        authors = None

    return (column_headings, authors)


def parse_author_file(document):
    """
    Given a filename to an author file, parse it
    """
    (column_headings, author_rows) = parse_author_data(document)
    return (column_headings, author_rows)


def parse_author_data(document):
    """
    Given author data - CSV with header rows - parse
    it and return an object representation
    """

    column_headings = None
    author_rows = []

    # open the file and parse it
    # https://docs.python.org/3/library/functions.html#open
    handle = io.open(
        document, "r", newline="", encoding="utf-8", errors="surrogateescape"
    )
    with handle as csvfile:
        filereader = csv.reader(csvfile)
        for row in filereader:
            # For now throw out header rows
            if filereader.line_num <= 3:
                pass
            elif filereader.line_num == 4:
                # Column headers
                column_headings = row
            else:
                author_rows.append(row)

    return (column_headings, author_rows)


def preprint_author_detail_list(document, doi_id, version):
    """
    get preprint author details from the document as a list
    note: CSV version column value 0 is the version 1
    note: logic depends on a CSV file sorted by doi_id and version
    """
    authors = []

    # Parse the author file
    (column_headings, author_rows) = parse_preprint_author_file(document)

    if not doi_id or not version:
        return (column_headings, None)

    if author_rows:
        # keep track of if the first version starts at above 0
        version_start = 0
        for fields in author_rows:
            # Check doi_id column value
            if doi_id is not None:
                if int(doi_id) != int(fields[0]):
                    continue
            # Check the version column value
            sheet_version = int(fields[1])
            sheet_appeal = fields[2]
            if sheet_appeal != "":
                version_start = 1
            if int(sheet_version) - version_start == int(version) - 1:
                fields = [entity_to_unicode(field) for field in fields]
                # Finish up, add the author to the list
                authors.append(fields)

    if len(authors) <= 0:
        authors = None

    return (column_headings, authors)


def parse_preprint_author_file(document):
    """
    Given a filename to a preprint author file, parse it
    """
    (column_headings, author_rows) = parse_author_data(document)
    return (column_headings, author_rows)


def is_corresponding_author(author_type_cde, dual_corr_author_ind):
    """
    Logic for checking whether an author row is for
    a corresponding author. Can be either "Corresponding Author"
    or "dual_corr_author_ind" column is 1
    """
    return bool(
        author_type_cde == "Corresponding Author" or dual_corr_author_ind == "1"
    )
