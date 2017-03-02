#!/bin/bash
set -e
source venv/bin/activate

# intentionally only an expanding subset of files
python -m pylint -E \
    *.py \
    activity/activity*.py \
    provider/article_structure.py \
    provider/imageresize.py \
    provider/lax_provider.py \
    provider/storage_provider.py \
    tests/activity/*.py \
    tests/provider/*.py
