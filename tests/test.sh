#±/bin/bash
source ../venv/bin/activate
for i in `ls features/*.feature`; do echo $i; lettuce $i -v 1; done
