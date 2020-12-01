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

# https://pip.pypa.io/en/stable/user_guide/#resolver-changes-2020
# '--no-deps': "If you don’t want pip to actually resolve dependencies, use the --no-deps option. 
# This is useful when you have a set of package versions that work together in reality, even though their metadata says that they conflict."
pip install --ignore-installed -r source-requirements.txt --no-deps
pip install -r requirements.txt --no-deps
# pip install -r source-requirements.txt --no-cache-dir # only if old revisions are still 'sticking'
rm source-requirements.txt
