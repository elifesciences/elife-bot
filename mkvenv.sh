#!/bin/bash
set -e

python=''
pybinlist=("python3.8" "python3")

for pybin in ${pybinlist[*]}; do
    which "$pybin" &> /dev/null || continue
    python=$pybin
    break
done

if [ -z "$python" ]; then
    echo "no usable python found, exiting"
    exit 1
fi

if [ ! -e "venv/bin/$python" ]; then
    echo "could not find venv/bin/$python, recreating venv"
    rm -rf venv
    $python -m venv venv
else
    echo "using $python"
fi
