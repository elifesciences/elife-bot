import os
import shutil


def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def delete_folder(folder, recursively=False):
    if recursively:
        shutil.rmtree(folder)
    else:
        os.rmdir(folder)


def delete_files_in_folder(folder):
    file_list = os.listdir(folder)
    for file_name in file_list:
        if os.path.isfile(folder+"/"+file_name):
            os.remove(folder+"/"+file_name)


def delete_directories_in_folder(folder):
    folder_list = os.listdir(folder)
    for dir in folder_list:
        if os.path.isdir(dir):
            delete_folder(dir, True)


def delete_everything_in_folder(self, folder):
    self.delete_files_in_folder(folder)