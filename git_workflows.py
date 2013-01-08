from git import *
import glob
import shutil

xml_repo_base = "/Users/ian/code/public-code/elife-articles"
pdf_repo_base = "/Users/ian/code/public-code/elife-pdfs"

xml_files = glob.glob("*.xml")
pdf_files = glob.glob("*.pdf")
print xml_files

repo = Repo(pdf_repo_base)
dirty = repo.is_dirty()
if not dirty:
	print "I'm clean!!"
	print "moving files into the repo"
	# move the files into the repo
	for f in pdf_files:
		shutil.move(f, pdf_repo_base + "/" + f)
		print "moved ", f 
	# add the files to the repo, commit and push to github
	git = repo.git
	git.add("*.pdf")
	print "adding pdf files to repo ..."
	print "comitting ..."
	git.commit(m="new batch")
	print "committed!"
	print "pushing to github!"
	git.push()
	print "pushed !"
