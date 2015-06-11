#!/bin/bash
# This script will start workers and deciders on both
#  dev and live environments
#  and using the python virtualenv in venv directory
# Run from the parent directory with "./scripts/run_candidate.sh"
alias ..='cd ..'
source /opt/elife-bot/venv/bin/activate && python decider.py -f 3 &
source /opt/elife-bot/venv/bin/activate && python decider.py -f 3 -e live &
source /opt/elife-bot/venv/bin/activate && python worker.py -f 5 &
source /opt/elife-bot/venv/bin/activate && python worker.py -f 5 -e live &
