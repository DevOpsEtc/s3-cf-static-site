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

read -p "Do you want to upload a copy to $domain? " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
  aws s3 cp $logs/$report s3://$domain
  echo -e "\nLog report now at http://$domain/$report"
  echo -e "\nRun this command to delete the log report:"
  echo -e "\naws s3 rm s3://$domain/$report"
fi

echo -e "\n\nGoodbye!"
