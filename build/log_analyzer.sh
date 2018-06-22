#!/usr/bin/env bash

type -p goaccess >/dev/null || { echo -e "goaccess Not Found!"; exit 1; }

# Sync logs from log bucket
aws s3 sync s3://log.$domain $site_path

# Generate log report
if [ $(uname) == 'Darwin' ]; then
  gunzip -c $logs/*.gz | goaccess -a -o \
    $logs/$report
  open $logs/$report
elif [ $(uname) == 'Linux' ]; then
  zcat $logs/*.gz | goaccess -a -o \
    $logs/$report
else
  echo -e "\nScript not supported on this OS"
  exit 1
fi
echo -e "\nLog report generated at $logs/$report"

echo -e "\n\nGoodbye!"
