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

# lsh@2022-12-12: upgrading from psutil 5.9.3 to 5.9.4 did not remove .so files compiled for 5.9.3
# switch_revision_update_instance later dies with and "ImportError: version conflict" when calling register.py
rm -f venv/lib/python*/site-packages/psutil/*.so

source venv/bin/activate

# 'pip' fixes issues installing wheel packages, hides deprecation warnings
# 'wheel' to allow installing wheels
# 'setuptools' fixes python-docx installation issue #594 
# - https://github.com/python-openxml/python-docx/issues/594
pip install wheel pip "setuptools>=40.6" --upgrade

pip install -r requirements.txt --ignore-installed
