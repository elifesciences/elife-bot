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