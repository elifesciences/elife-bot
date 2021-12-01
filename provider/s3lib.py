import re
import boto.s3


"""
Functions for reuse concerning Amazon s3 and buckets
"""


def get_s3_key_names_from_bucket(
    bucket,
    key_type="key",
    prefix=None,
    delimiter="/",
    headers=None,
    file_extensions=None,
):
    """
    Given a connected boto bucket object, and optional parameters,
    from the prefix (folder name), get the s3 key names for
    key_type objects, optionally that match a particular
    list of file extensions
    key_type = "key" then look for s3 objects
    key_type = "prefix" then look for folders (also s3 objects of a different type)
    """
    s3_keys = get_s3_keys_from_bucket(
        bucket, key_type, prefix, delimiter, headers, file_extensions
    )
    s3_key_names = []
    # Convert to key names instead of objects to make it testable later
    for key in s3_keys:
        s3_key_names.append(key.name)

    # Filter by file_extension
    if file_extensions is not None:
        s3_key_names = filter_list_by_file_extensions(s3_key_names, file_extensions)

    return s3_key_names


def get_s3_keys_from_bucket(
    bucket,
    key_type="key",
    prefix=None,
    delimiter="/",
    headers=None,
    file_extensions=None,
):

    s3_keys = []

    # Get a list of S3 objects
    bucketList = bucket.list(prefix=prefix, delimiter=delimiter, headers=headers)

    for item in bucketList:
        # Can loop through each item and search for objects
        if key_type == "key":
            if isinstance(item, boto.s3.key.Key):
                s3_keys.append(item)
        elif key_type == "prefix":
            if isinstance(item, boto.s3.prefix.Prefix):
                s3_keys.append(item)

    return s3_keys


def filter_list_by_file_extensions(s3_key_names, file_extensions):
    """
    Given a list of s3_key_names, and a list of file_extensions
    filter out all but the allowed file extensions
    Each file extension should start with a . dot
    """
    good_s3_key_names = []
    for name in s3_key_names:
        match = False
        for ext in file_extensions:
            # Match file extension as the end of the string and escape the dot
            pattern = ".*\\" + ext + "$"
            if re.search(pattern, name) is not None:
                match = True
        if match is True:
            good_s3_key_names.append(name)

    return good_s3_key_names


def latest_pmc_zip_revision(doi_id, s3_key_names):
    """
    Given a list of zip file names from the PMC zip folder on S3,
    look for the ones matching the article doi_id
    and if there is more than one then return the latest revision, if applicable
    """
    s3_key_name = None

    name_matches = []
    for key_name in s3_key_names:
        name_match = "-" + str(doi_id).zfill(5)
        if name_match in key_name:
            name_matches.append(key_name)

    if len(name_matches) == 1:
        s3_key_name = name_matches[0]
    else:
        # Look for latest revision number
        highest_revision = None
        for key_name in name_matches:

            revision_match = re.match(r".*r(.*)\.zip$", key_name)

            if revision_match is None:
                if highest_revision is None:
                    # First value with no revision on it
                    s3_key_name = key_name
            elif revision_match is not None:
                # Use either the first revision number found or the highest revision number
                if highest_revision is None or (
                    highest_revision
                    and int(revision_match.group(1)) > int(highest_revision)
                ):
                    s3_key_name = key_name
                    highest_revision = revision_match.group(1)

    return s3_key_name
