#!/bin/bash
set -e

if [ "$ENVIRONMENT_NAME" == "ci" ]; then
    rm -rf venv/
fi

. mkvenv.sh

echo "Virtualenv Python: $(venv/bin/python --version)"

# remove any old compiled python files
find ./ -maxdepth 1 -name '*.pyc' -delete
find provider/ -maxdepth 1 -name '*.pyc' -delete
find activity/ -maxdepth 1 -name '*.pyc' -delete
find workflow/ -maxdepth 1 -name '*.pyc' -delete
find starter/ -maxdepth 1 -name '*.pyc' -delete
find S3utility/ -maxdepth 1 -name '*.pyc' -delete

source venv/bin/activate

# fixes issues installing wheel packages, hides deprecation warnings
pip install pip --upgrade

# fixes python-docx issue #594 
# https://github.com/python-openxml/python-docx/issues/594
pip install "setuptools>=40.6" --upgrade

grep "git+" requirements.txt > source-requirements.txt
#pip uninstall -r source-requirements.txt -y
pip install --ignore-installed -r source-requirements.txt
pip install -r requirements.txt
# pip install -r source-requirements.txt --no-cache-dir # only if old revisions are still 'sticking'
rm source-requirements.txt
