import calendar
from operator import itemgetter
import csv
import re
import os
import sys
import io
from ejpcsvparser.utils import entity_to_unicode
from provider.storage_provider import storage_context
from provider import utils

"""
EJP data provider
Connects to S3, discovers, downloads, and parses files exported by EJP
"""


class EJP:
    def __init__(self, settings=None, tmp_dir=None):
        self.settings = settings
        self.tmp_dir = tmp_dir

        # Default tmp_dir if not specified
        self.tmp_dir_default = "ejp_provider"

        # Default S3 bucket name
        self.bucket_name = None
        if self.settings is not None:
            self.bucket_name = self.settings.ejp_bucket

        # Some EJP file types we expect
        self.author_default_filename = "authors.csv"
        self.editor_default_filename = "editors.csv"

    def write_content_to_file(self, filename, content, mode="wb"):
        "write the content to a file in the tmp_dir"
        document = None
        # set the document path
        try:
            document_path = os.path.join(self.get_tmp_dir(), filename)
        except TypeError:
            document_path = None
        # write the content to the file
        try:
            with open(document_path, mode) as fp:
                fp.write(content)
                # success, set the document value to return
                document = document_path
        except (TypeError, IOError):
            document = None
        return document

    def parse_author_file(self, document):
        """
        Given a filename to an author file, parse it
        """
        (column_headings, author_rows) = self.parse_author_data(document)
        return (column_headings, author_rows)

    def parse_author_data(self, document):
        """
        Given author data - CSV with header rows - parse
        it and return an object representation
        """

        column_headings = None
        author_rows = []

        # open the file and parse it
        if sys.version_info[0] < 3:
            handle = open(document, "rb")
        else:
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

    def get_authors(self, doi_id=None, corresponding=None, local_document=None):
        """
        Get a list of authors for an article
          If doi_id is None, return all authors
          If corresponding is
            True, return corresponding authors
            False, return all but corresponding authors
            None, return all authors
          If document is None, find the most recent authors file
        """
        authors = []
        # Check for the document
        if local_document is None:
            # No document? Find it on S3, save the content to
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
            document = self.write_content_to_file(
                self.author_default_filename, contents
            )
        else:
            # copy the document to the tmp_dir if provided
            with open(local_document, "rb") as fp:
                document = self.write_content_to_file(
                    self.author_default_filename, fp.read()
                )

        # Parse the author file
        (column_headings, author_rows) = self.parse_author_file(document)

        if author_rows:
            for fields in author_rows:
                add = True
                # Check doi_id column value
                if doi_id is not None:
                    if int(doi_id) != int(fields[0]):
                        add = False
                # Check corresponding column value
                if corresponding and add is True:

                    author_type_cde = fields[4]
                    dual_corr_author_ind = fields[5]
                    is_corr = self.is_corresponding_author(
                        author_type_cde, dual_corr_author_ind
                    )

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

    def is_corresponding_author(self, author_type_cde, dual_corr_author_ind):
        """
        Logic for checking whether an author row is for
        a corresponding author. Can be either "Corresponding Author"
        or "dual_corr_author_ind" column is 1
        """
        is_corr = None

        if author_type_cde == "Corresponding Author" or dual_corr_author_ind == "1":
            is_corr = True
        else:
            is_corr = False

        return is_corr

    def parse_editor_file(self, document):
        """
        Given a filename to an editor file, parse it
        """
        (column_headings, editor_rows) = self.parse_editor_data(document)
        return (column_headings, editor_rows)

    def parse_editor_data(self, document):
        """
        Given editor data - CSV with header rows - parse
        it and return an object representation
        """

        column_headings = None
        editor_rows = []

        # open the file and parse it
        if sys.version_info[0] < 3:
            handle = open(document, "rb")
        else:
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
                    editor_rows.append(row)

        return (column_headings, editor_rows)

    def get_editors(self, doi_id=None, local_document=None):
        """
        Get a list of editors for an article
          If doi_id is None, return all editors
          If document is None, find the most recent editors file
        """
        editors = []
        # Check for the document
        if local_document is None:
            storage = storage_context(self.settings)
            s3_key_name = self.find_latest_s3_file_name(file_type="editor")
            s3_resource = (
                self.settings.storage_provider
                + "://"
                + self.bucket_name
                + "/"
                + s3_key_name
            )
            contents = storage.get_resource_as_string(s3_resource)
            document = self.write_content_to_file(
                self.editor_default_filename, contents
            )
        else:
            # copy the document to the tmp_dir if provided
            with open(local_document, "rb") as fp:
                document = self.write_content_to_file(
                    self.editor_default_filename, fp.read()
                )

        # Parse the file
        (column_headings, editor_rows) = self.parse_editor_file(document)

        if editor_rows:
            for a in editor_rows:
                add = True
                # Check doi_id column value
                if doi_id is not None:
                    if int(doi_id) != int(a[0]):
                        add = False

                # Finish up, add the author if we should
                if add is True:
                    editors.append(a)

        if len(editors) <= 0:
            editors = None

        return (column_headings, editors)

    def find_latest_s3_file_name(self, file_type, file_list=None):
        """
        Given the file_type, find the name of the S3 key for the object
        that is the latest file in the S3 bucket
          file_type options: author, editor
        Optional: for running tests, provide a file_list without connecting to S3
        """

        s3_key_name = None

        # For each file_type, specify a unique file name fragment to filter on
        #  with regular expression search
        fn_fragment = {}
        fn_fragment["author"] = r"ejp_query_tool_query_id_15a\)_Accepted_Paper_Details"
        fn_fragment["editor"] = r"ejp_query_tool_query_id_15b\)_Accepted_Paper_Details"
        fn_fragment["poa_manuscript"] = "ejp_query_tool_query_id_POA_Manuscript"
        fn_fragment["poa_author"] = "ejp_query_tool_query_id_POA_Author"
        fn_fragment["poa_license"] = "ejp_query_tool_query_id_POA_License"
        fn_fragment["poa_subject_area"] = "ejp_query_tool_query_id_POA_Subject_Area"
        fn_fragment["poa_received"] = "ejp_query_tool_query_id_POA_Received"
        fn_fragment[
            "poa_research_organism"
        ] = "ejp_query_tool_query_id_POA_Research_Organism"
        fn_fragment["poa_abstract"] = "ejp_query_tool_query_id_POA_Abstract"
        fn_fragment["poa_title"] = "ejp_query_tool_query_id_POA_Title"
        fn_fragment["poa_keywords"] = "ejp_query_tool_query_id_POA_Keywords"
        fn_fragment["poa_group_authors"] = "ejp_query_tool_query_id_POA_Group_Authors"
        fn_fragment["poa_datasets"] = "ejp_query_tool_query_id_POA_Datasets"
        fn_fragment["poa_funding"] = "ejp_query_tool_query_id_POA_Funding"
        fn_fragment["poa_ethics"] = "ejp_query_tool_query_id_POA_Ethics"

        # first try to locate the s3 key by looking for the expected name
        s3_key_name = self.latest_s3_file_name_by_convention(fn_fragment, file_type)

        if not s3_key_name:
            # find s3_key_name by checking for the latest modified date on the s3 key
            s3_key_name = self.latest_s3_file_name_by_modified_date(
                fn_fragment, file_type, file_list
            )

        return s3_key_name

    def latest_s3_file_name_by_convention(self, fn_fragment, file_type):
        "concatenate the expected s3 file name and check if it exists in the bucket"
        date_string = utils.set_datestamp("_")
        # remove backslashes from regular expression fragments
        clean_fn_fragment = fn_fragment[file_type].replace("\\", "")
        file_name_to_match = "%s_%s_eLife.csv" % (clean_fn_fragment, date_string)
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
            s = sorted(
                good_file_list, key=itemgetter("last_modified_timestamp"), reverse=True
            )

            if len(s) > 0:
                # We still have a list, take the name of the first one
                s3_key_name = s[0]["name"]

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

    def get_tmp_dir(self):
        """
        Get the temporary file directory, but if not set
        then make the directory
        """
        if self.tmp_dir:
            return self.tmp_dir
        else:
            self.tmp_dir = self.tmp_dir_default

        return self.tmp_dir
