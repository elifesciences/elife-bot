#!/bin/bash
set -e
source venv/bin/activate
rm -f build/junit.xml
./lint.sh
bash ./travis-test.sh
 

