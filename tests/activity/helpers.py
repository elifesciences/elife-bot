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
    fileList = os.listdir(folder)
    for fileName in fileList:
        if os.path.isfile(folder+"/"+fileName):
            os.remove(folder+"/"+fileName)


def delete_directories_in_folder(folder):
    folderList = os.listdir(folder)
    for dir in folderList:
        if os.path.isdir(dir):
            delete_folder(dir, True)


def delete_everything_in_folder(self, folder):
    self.delete_files_in_folder(folder)