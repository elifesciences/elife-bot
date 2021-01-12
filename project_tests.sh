#!/bin/bash
set -e
source venv/bin/activate
rm -f build/junit.xml
./lint.sh
export BOTO_CONFIG=/dev/null
python -m pytest --junitxml=build/junit.xml
