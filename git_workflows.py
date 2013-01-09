from git import *
import glob
import shutil
from optparse import OptionParser

XML_REPO_BASE = "/Users/ian/code/public-code/elife-articles"
PDF_REPO_BASE = "/Users/ian/code/public-code/elife-pdfs"

xml_files = glob.glob("*.xml")

def move_files_into_repo(files, path_to_repo):
    for filename in files:
        shutil.move(filename, path_to_repo + "/" + filename)   

def update_local_and_remote(repo):
    git = repo.git
    git.add("*")
    print "adding pdf files to repo ..."
    print "comitting ..."
    git.commit(m="new batch")
    print "committed!"
    print "pushing to github!"
    git.push()
    print "pushed !"

if __name__ == "__main__":
    # Add options
    parser = OptionParser()
    parser.add_option("-l", "--list", action="store_true", dest="list", help="lists new files to be added to the repo", default="true")
    parser.add_option("-a", "--add", action="store_false", dest="list", help="add files to the repo, and commit")
    parser.add_option("-t", "--type", dest="type", help="pick file types", default="xml")
    (options, args) = parser.parse_args()

    if options.type == "pdf":
        files = glob.glob("*.pdf")
        repo_base = PDF_REPO_BASE
    else:
        files = glob.glob("*.xml")
        repo_base = XML_REPO_BASE

    repo = Repo(repo_base)

    if options.list: 
        print "I'm going to list the files"
        print files
    else:
        print "I'm going to move the files, and commit the repo"
        #move_files_into_repo(repo_base)
        if repo.is_dirty():
            raise Exception("repo is dirty, aborting")
        else:
            print "OK, things look OK for now"
