#±/bin/bash
set -e
source venv/bin/activate
cd tests/
for i in `ls features/*.feature`; do echo $i; lettuce $i -v 1; done
cd -
bash ./travis-test.sh
 

