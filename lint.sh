#!/bin/bash
set -e
source venv/bin/activate

# intentionally only the script files in the root folder
python -m pylint -E \
    *.py \
    activity/activity_Update*.py \
    activity/activity_Pubmed*.py \
    provider/article_structure.py \
    provider/imageresize.py \
    provider/lax_provider.py \
    provider/storage_provider.py \
    tests/provider/*.py
