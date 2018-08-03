#!/bin/bash
set -e # everything must succeed.
export BOTO_CONFIG=/dev/null
pip install -r requirements.txt
