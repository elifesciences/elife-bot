#!/bin/bash
export BOTO_CONFIG=/dev/null
python -m pytest --junitxml=build/junit.xml
