#!/bin/bash
export BOTO_CONFIG="/tmp/nowhere"
python -m pytest --junitxml=build/junit.xml
