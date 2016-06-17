#!/bin/bash
set -e # everything must succeed.
pip install -r requirements.txt
git clone https://github.com/elifesciences/elife-poa-xml-generation.git ../elife-poa-xml-generation