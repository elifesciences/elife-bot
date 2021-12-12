#!/bin/bash
# updates Pipfile.lock and regenerates the requirements.txt file.
# if a package and a version are passed in, then just that package (and it's dependencies) will be updated.

set -e

# optional
package="$1"
version="$2"

# create/update existing venv
rm -rf venv/

# whatever your preferred version of python is, eLife needs to support python3.6 (Ubuntu 18.04)
python3.6 -m venv venv

# prefer using wheels to compilation
source venv/bin/activate
pip install pip wheel --upgrade

if [ -n "$package" ]; then
    # updates a single package to a specific version.

    pip install -r requirements.txt

    # make Pipenv install exactly what we want (==).
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sed --in-place --regexp-extended "s/$package = \".+\"/$package = \"==$version\"/" Pipfile
    else
        sed -i '' -E "s/$package = \".+\"/$package = \"==$version\"/" Pipfile
    fi

    # the envvar is necessary otherwise Pipenv will use it's own .venv directory.
    VIRTUAL_ENV="venv" pipenv install --keep-outdated "$package==$version"

    # relax the constraint again (~=).
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sed --in-place --regexp-extended "s/$package = \".+\"/$package = \"~=$version\"/" Pipfile
    else
        sed -i '' -E "s/$package = \".+\"/$package = \"~=$version\"/" Pipfile
    fi
else
    # updates the Pipfile.lock file and then installs the newly updated dependencies.
    # the envvar is necessary otherwise Pipenv will use it's own .venv directory.
    VIRTUAL_ENV="venv" pipenv update --dev
fi

datestamp=$(date +"%Y-%m-%d") # long form to support linux + bsd
echo "# file generated $datestamp - see update-dependencies.sh" > requirements.txt
# lsh@2021-11-29: re 'pkg-resources': https://github.com/pypa/pip/issues/4022
VIRTUAL_ENV="venv" pipenv run pip freeze | grep -v pkg_resources >> requirements.txt
