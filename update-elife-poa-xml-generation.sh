#!/bin/bash
set -e

default_folder="/opt/elife-poa-xml-generation"
folder="${1-$default_folder}"
cd $folder
git fetch
git checkout master
git pull origin master
sha1=$(git rev-parse HEAD) 
cd -
echo $sha1 > elife-poa-xml-generation.sha1

