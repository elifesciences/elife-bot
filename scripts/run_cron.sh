#!/bin/bash
alias ..='cd ..'
source /opt/elife-bot/venv/bin/activate && python cron.py > /dev/null
source /opt/elife-bot/venv/bin/activate && python cron.py -e live > /dev/null