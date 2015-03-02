import boto.s3
import re

"""
Functions for reuse concerning Amazon s3 and buckets
"""

def get_s3_key_names_from_bucket(bucket, prefix = None, delimiter = '/', headers = None, file_extensions = None):
    """
    Given a connected boto bucket object, and optional parameters,
    from the prefix (folder name), get the s3 key names for
    non-folder objects, optionally that match a particular
    list of file extensions
    """
    s3_keys = []
    s3_key_names = []
    
    # Get a list of S3 objects
    bucketList = bucket.list(prefix = prefix, delimiter = delimiter, headers = headers)

    for item in bucketList:
      if(isinstance(item, boto.s3.key.Key)):
        # Can loop through each prefix and search for objects
        s3_keys.append(item)
    
    # Convert to key names instead of objects to make it testable later
    for key in s3_keys:
        s3_key_names.append(key.name)
    
    # Filter by file_extension
    if file_extensions is not None:
        s3_key_names = filter_list_by_file_extensions(s3_key_names, file_extensions)
        
    return s3_key_names

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
            if(re.search(pattern, name) is not None):
                match = True
        if match is True:
            good_s3_key_names.append(name)
    
    return good_s3_key_names
