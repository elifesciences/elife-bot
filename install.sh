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

if pip list | grep elifetools; then
    pip uninstall -y elifetools
fi
if pip list | grep elifearticle; then
    pip uninstall -y elifearticle
fi
if pip list | grep elifecrossref; then
    pip uninstall -y elifecrossref
fi
if pip list | grep elifepubmed; then
    pip uninstall -y elifepubmed
fi
if pip list | grep ejpcsvparser; then
    pip uninstall -y ejpcsvparser
fi
if pip list | grep jatsgenerator; then
    pip uninstall -y jatsgenerator
fi
if pip list | grep packagepoa; then
    pip uninstall -y packagepoa
fi
if pip list | grep digestparser; then
    pip uninstall -y digestparser
fi
pip install -r requirements.txt

