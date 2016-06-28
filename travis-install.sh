#!/bin/bash
set -e # everything must succeed.
ln -s settings-example.py settings.py
pip install -r requirements.txt
git clone https://github.com/elifesciences/elife-poa-xml-generation.git ../elife-poa-xml-generation
cp ../elife-poa-xml-generation/example-settings.py ../elife-poa-xml-generation/settings.py
