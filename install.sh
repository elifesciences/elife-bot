#!/bin/bash
set -e

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    virtualenv --python=`which python2` venv
fi

source venv/bin/activate

if pip list | grep elifetools; then
    pip uninstall -y elifetools
fi
pip install -r requirements.txt

