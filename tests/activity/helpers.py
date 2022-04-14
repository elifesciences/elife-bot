import email
import os
import shutil
import zipfile
from digestparser.objects import Digest, Image
from provider import utils
from provider.article import article


def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def delete_folder(folder, recursively=False):
    if recursively:
        shutil.rmtree(folder)
    else:
        os.rmdir(folder)


def delete_files_in_folder(folder, filter_out=[]):
    file_list = os.listdir(folder)
    for file_name in file_list:
        if file_name in filter_out:
            continue
        if os.path.isfile(folder + "/" + file_name):
            os.remove(folder + "/" + file_name)


def delete_directories_in_folder(folder):
    folder_list = os.listdir(folder)
    for dir in folder_list:
        dir_path = os.path.join(folder, dir)
        if os.path.isdir(dir_path):
            delete_folder(dir_path, True)


def delete_everything_in_folder(self, folder):
    self.delete_files_in_folder(folder)


def instantiate_article(article_type, doi, is_poa=None, was_ever_poa=None):
    "for testing purposes, generate an article object"
    article_object = article()
    article_object.article_type = article_type
    article_object.doi = doi
    article_object.doi_id = utils.pad_msid(utils.msid_from_doi(doi))
    article_object.is_poa = is_poa
    article_object.was_ever_poa = was_ever_poa
    return article_object


def create_digest(
    author=None, doi=None, text=None, title=None, image=None, summary=None
):
    "for testing generate a Digest object an populate it"
    digest_content = Digest()
    digest_content.author = author
    digest_content.doi = doi
    if text:
        digest_content.text = text
    if title:
        digest_content.title = title
    if image:
        digest_content.image = image
    if summary:
        digest_content.summary = summary
    return digest_content


def create_digest_image(caption=None, file_name=None):
    "for testing generate a Digest Image object an populate it"
    digest_image = Image()
    if caption:
        digest_image.caption = caption
    if file_name:
        digest_image.file = file_name
    return digest_image


def body_from_multipart_email_string(email_string):
    """Given a multipart email string, convert to Message and return decoded body"""
    body = None
    email_message = email.message_from_string(email_string)
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True)
    return body


def expanded_folder_resources(zip_file_path, directory):
    "expand the zip file to the directory and return a list resources"
    with zipfile.ZipFile(zip_file_path, "r") as open_zipfile:
        open_zipfile.extractall(path=directory)
        resources = open_zipfile.namelist()
    return resources


def expanded_folder_bucket_resources(directory, expanded_folder, zip_file_path):
    "populate the TempDirectory with files from zip_filename to mock a bucket folder in tests"
    directory.makedir(expanded_folder)
    directory_s3_folder_path = os.path.join(
        directory.path,
        expanded_folder,
    )
    resources = expanded_folder_resources(zip_file_path, directory_s3_folder_path)
    return resources


def populate_storage(from_dir, to_dir, filenames, sub_dir=""):
    "copy filesnames from from_dir to to_dir into the sub_dir for test bucket resources"
    resources = []
    for filename in filenames:
        from_filename = os.path.join(from_dir, filename)
        to_resource = os.path.join(sub_dir, filename)
        to_filename = os.path.join(to_dir, to_resource)
        resources.append(to_resource)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(to_filename), exist_ok=True)
        shutil.copy(from_filename, to_filename)
    return resources
