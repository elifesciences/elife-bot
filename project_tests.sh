#!/bin/bash
set -e
source venv/bin/activate
cd tests/
for i in `ls features/*.feature`; do echo $i; lettuce $i; done
cd -
rm -f build/junit.xml
./lint.sh
bash ./travis-test.sh
 

