#!/bin/bash
# This script will start workers and deciders on both
#  dev and live environments
#  optimised for Amazon EC2 microinstance
#  (5 workers and 3 deciders on each environment
# Run from the parent directory with "./scripts/run_micro.sh"
alias ..='cd ..'
sudo python decider.py -f 3 &
sudo python decider.py -f 3 -e live &
sudo python worker.py -f 5 &
sudo python worker.py -f 5 -e live &