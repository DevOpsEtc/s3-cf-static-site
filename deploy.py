#!/usr/bin/env python3

import json
import boto3
from botocore.exceptions import ClientError
from colorama import init, Fore
from halo import Halo

def main():
    """Create/Update/Delete CloudFormation stack to deploy S3 static website.

    If the CloudFormation stack does not already exists, create it and deploy:
        - IAM groups and users
        - IAM policy with S3 and CloudFormation permissions
        - S3 buckets and respective configuration
    if already exists, prompt to update (teardown/rebuild) or delete.
    """

    region = 'us-west-1' # overide any local aws-cli config
    domain_name = 'DevOpsEtc.com'
    iam_group_user = 'Blog-Users'
    iam_group_user_desc = 'Blog Users'
    iam_group_admin = 'Blog-Admins'
    iam_group_admin_desc = 'Blog Admins'
    iam_user = 'Blog-User'
    iam_admin = 'Blog-Admin'
    iam_policy_iam = 'Blog-Pol-IAM'
    iam_policy_s3 = 'Blog-Pol-S3'
    cf_stack = 'Blog-Stack'
    cf_params = 'stack_params.json'
    cf_template = 'blog_stack.yaml'
    s3_bucket_cdn = domain_name + '-cdn' # bucket for website
    s3_bucket_log = domain_name + '-log' # bucket for access log

    init(autoreset=True) # colorama: automatically reset style after each call

    cf = boto3.client('cloudformation')

    try:
        cf.describe_stacks(StackName=cf_stack)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stack(cf, cf_stack, cf_params, cf_template)
    else:
        print('\nStack Already Exists:',Fore.RED + cf_stack + '!')
        prompt = Fore.YELLOW + '\nUpdate|Delete|Cancel (U|D|C): ' + Fore.RESET
        while "input invalid":
            reply = str(input(prompt)).lower().strip()
            if reply[:1] == 'u':
                update_stack(cf, cf_stack, cf_params, cf_template)
                return True
            if reply[:1] == 'd':
                delete_stack(cf, cf_stack)
                return False
            if reply[:1] == 'c':
                return False

def launch_stack(cf, cf_stack, cf_params, cf_template):
    print('')
    spin_start = '\nLaunching Stack...'
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    with open(cf_params, 'r') as f:
        params = json.load(f)

    with open(cf_template, 'r') as f:
        template = f.read()

    cf.create_stack(
        StackName=cf_stack,
        TemplateBody=template,
        Parameters=params,
        TimeoutInMinutes=5,
        Capabilities=['CAPABILITY_NAMED_IAM'],
        OnFailure='ROLLBACK'
    )

    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Created!'
    spinner.succeed(text=spin_success)

def update_stack(cf, cf_stack, cf_params, cf_template):
    print('')
    spin_start = '\nUpdating Stack...'
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    with open(cf_params, 'r') as f:
        params = json.load(f)

    with open(cf_template, 'r') as f:
        template = f.read()

    cf.update_stack(
        StackName=cf_stack,
        TemplateBody=template,
        Parameters=params,
        Capabilities=['CAPABILITY_NAMED_IAM']
    )

    waiter = cf.get_waiter('stack_update_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Updated!'
    spinner.succeed(text=spin_success)



def delete_stack(cf, cf_stack):
    print('')
    spin_start = '\nDeleting Stack...'
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    cf.delete_stack(StackName=cf_stack)

    waiter = cf.get_waiter('stack_delete_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Deleted!'
    spinner.succeed(text=spin_success)

if __name__ == '__main__':
    main()
