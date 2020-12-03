#!/bin/bash
# updates Pipfile.lock and regenerates the requirements.txt file
set -e

# create/update existing venv
rm -rf venv/

# whatever your preferred version of python is, eLife needs to support python3.6 (Ubuntu 18.04)
python3.6 -m venv venv

# prefer using wheels to compilation
source venv/bin/activate
pip install wheel

# updates the Pipfile.lock file and then installs the newly updated dependencies.
# the envvar is necessary otherwise pipenv will use it's own .venv directory.
VIRTUAL_ENV="venv" pipenv update --dev

datestamp=$(date -I)
echo "# file generated $datestamp - see update-dependencies.sh" > requirements.txt
VIRTUAL_ENV="venv" pipenv run pip freeze >> requirements.txt
