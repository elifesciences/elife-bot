#!/bin/bash
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

# remove any old compiled python files
find ./ -maxdepth 1 -name '*.pyc' -delete
find provider/ -maxdepth 1 -name '*.pyc' -delete
find activity/ -maxdepth 1 -name '*.pyc' -delete
find workflow/ -maxdepth 1 -name '*.pyc' -delete
find starter/ -maxdepth 1 -name '*.pyc' -delete
find S3utility/ -maxdepth 1 -name '*.pyc' -delete

source venv/bin/activate
grep "git+" requirements.txt > source-requirements.txt
pip uninstall -r source-requirements.txt -y
pip install -r requirements.txt
# pip install -r source-requirements.txt --no-cache-dir # only if old revisions are still 'sticking'
rm source-requirements.txt
