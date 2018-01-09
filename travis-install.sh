#!/bin/bash
set -e # everything must succeed.
export BOTO_CONFIG=/dev/null
pip install -r requirements.txt
git clone https://github.com/elifesciences/elife-poa-xml-generation.git ../elife-poa-xml-generation
cp ../elife-poa-xml-generation/example-settings.py ../elife-poa-xml-generation/settings.py
