import os
import shutil
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
        if os.path.isfile(folder+"/"+file_name):
            os.remove(folder+"/"+file_name)


def delete_directories_in_folder(folder):
    folder_list = os.listdir(folder)
    for dir in folder_list:
        if os.path.isdir(dir):
            delete_folder(dir, True)


def delete_everything_in_folder(self, folder):
    self.delete_files_in_folder(folder)


def instantiate_article(article_type, doi, is_poa=None, was_ever_poa=None):
    "for testing purposes, generate an article object"
    article_object = article()
    article_object.article_type = article_type
    article_object.doi = doi
    article_object.doi_id = article_object.get_doi_id(doi)
    article_object.is_poa = is_poa
    article_object.was_ever_poa = was_ever_poa
    return article_object
