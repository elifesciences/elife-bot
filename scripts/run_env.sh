#!/bin/bash
# This script will start workers and deciders on both
#  in the environment as you specify in the first argument
#  and using the python virtualenv in venv directory
# Run from the parent directory e.g. "./scripts/run_env.sh dev"
if [[ $1 == "" ]]; then
    echo "usage: you must supply a first argument for the env to run"
    exit 1
fi
alias ..='cd ..'
source /opt/elife-bot/venv/bin/activate && python decider.py -f 3 -e $1 &
source /opt/elife-bot/venv/bin/activate && python worker.py -f 5 -e $1 &
source /opt/elife-bot/venv/bin/activate && python queue_worker.py -f 3 -e $1 &
source /opt/elife-bot/venv/bin/activate && python queue_workflow_starter.py -f 5 -e $1 &
source /opt/elife-bot/venv/bin/activate && python shimmy.py -e $1 &
