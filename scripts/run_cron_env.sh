#!/bin/bash
# Run from the parent directory e.g. "./scripts/run_cron_env.sh live"
alias ..='cd ..'
source /opt/elife-bot/venv/bin/activate && python cron.py -e $1 > /dev/null
