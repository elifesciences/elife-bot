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
if pip list | grep elifearticle; then
    pip uninstall -y elifearticle
fi
if pip list | grep elifecrossref; then
    pip uninstall -y elifecrossref
fi
if pip list | grep elifepubmed; then
    pip uninstall -y elifepubmed
fi
pip install -r requirements.txt

