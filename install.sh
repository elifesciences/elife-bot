#!/bin/bash
set -e

python=''
pybinlist=("python3.6" "python3.5" "python3.4")

for pybin in ${pybinlist[*]}; do
    which "$pybin" &> /dev/null || continue
    python=$pybin
    break
done

if [ -z "$python" ]; then
    echo "no usable python found, exiting"
    exit 1
fi

echo "Found Python: $($python --version)"

if [ "$ENVIRONMENT_NAME" == "ci" ]; then
    rm -rf venv/
fi

if [ ! -d venv ]; then
    # build venv if one doesn't exist
    $python -m venv venv
fi

echo "Virtualenv Python: $(venv/bin/python --version)"

pip install --upgrade pip

# remove any old compiled python files
find ./ -maxdepth 1 -name '*.pyc' -delete
find provider/ -maxdepth 1 -name '*.pyc' -delete
find activity/ -maxdepth 1 -name '*.pyc' -delete
find workflow/ -maxdepth 1 -name '*.pyc' -delete
find starter/ -maxdepth 1 -name '*.pyc' -delete
find S3utility/ -maxdepth 1 -name '*.pyc' -delete

source venv/bin/activate
grep "git+" requirements.txt > source-requirements.txt
#pip uninstall -r source-requirements.txt -y
pip install --ignore-installed -r source-requirements.txt
pip install -r requirements.txt
# pip install -r source-requirements.txt --no-cache-dir # only if old revisions are still 'sticking'
rm source-requirements.txt
