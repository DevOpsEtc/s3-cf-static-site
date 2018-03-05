#!/usr/bin/env python3

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

    region = 'us-east-1' # overide local AWS config; needed for certificate
    profile = 'Static-Site'
    cf_stack = profile + '-Stack'
    cf_template = 's3.cfn.yaml'
    domain = 'devopsetc.com'
    # account = boto3.client('sts').get_caller_identity()['Account']
    params =  [
        {"ParameterKey": "DomainName","ParameterValue": domain},
        {"ParameterKey": "GroupName","ParameterValue": profile}
    ]
    cf = boto3.client('cloudformation')

    init(autoreset=True) # colorama: automatically reset style after each call

    # set which AWS credentials to use for this session
    # boto3.setup_default_session(profile_name=profile)

    try:
        cf.describe_stacks(StackName=cf_stack)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stack(cf, cf_stack, cf_template, params)
    else:
        print('\n' + Fore.RED + cf_stack + 'Already Exists!\n')
        prompt = Fore.YELLOW + 'Update|Delete|Cancel (U|D|C): ' + Fore.RESET
        while "input invalid":
            reply = str(input(prompt)).lower().strip()
            if reply[:1] == 'u':
                update_stack(cf, cf_stack, cf_template, params)
                return True
            if reply[:1] == 'd':
                delete_stack(cf, cf_stack, domain)
                return False
            if reply[:1] == 'c':
                return False

def launch_stack(cf, cf_stack, cf_template, params):
    print('')
    spin_start = '\nLaunching Stack...'
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    with open(cf_template, 'r') as f:
        template = f.read()

    cf.create_stack(
        StackName=cf_stack,
        TemplateBody=template,
        Parameters=params,
        TimeoutInMinutes=10,
        Capabilities=['CAPABILITY_NAMED_IAM'],
        OnFailure='ROLLBACK'
    )

    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Created!'
    spinner.succeed(text=spin_success)

def update_stack(cf, cf_stack, cf_template, params):
    try:
        print('')
        spin_start = '\nUpdating Stack...'
        spinner = Halo(text=spin_start, spinner='circleHalves')
        spinner.start()

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
    except ClientError as e:
        error_string = 'No updates are to be performed.'
        if e.response['Error']['Message'].endswith(error_string):
            print(Fore.RED + error_string)
            quit()

def delete_stack(cf, cf_stack, domain):
    print('')
    spin_start = '\nDeleting Stack...'
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    # Bucket can't be deleted unless it's empty
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(domain)
    bucket_log = s3.Bucket(domain + '-log')
    bucket.objects.all().delete()
    bucket_log.objects.all().delete()

    cf.delete_stack(StackName=cf_stack)

    waiter = cf.get_waiter('stack_delete_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Deleted!'
    spinner.succeed(text=spin_success)

if __name__ == '__main__':
    main()
