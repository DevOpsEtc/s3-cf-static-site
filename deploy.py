#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
from colorama import init, Fore
from halo import Halo

def main():
    """Create/Update/Delete CloudFormation stack to deploy S3 static website.

    Launches a CloudFormation stack that creates:
        - One IAM group
        - One IAM group policy
        - One IAM user
        - Two S3 buckets
        - One ACM SSL/TLS certificate
        - One CloudFront distribution resource

    Also, wrapper script checks for existing stack and if found, prompts to
    push CloudFormation template changes via an update or rollback deployment
    via a delete.
    """

    region_cert = 'us-east-1' # overide local AWS config; needed for certificate
    profile = 'Static-Site'
    cf_stack = profile + '-Stack'
    cf_stack_cert = profile + '-Cert-Stack'
    cf_temp = 'cfn/site.cfn.yaml'
    cf_temp_cert = 'cfn/cert.cfn.yaml'
    domain = 'devopsetc.com'
    params =  [
        {"ParameterKey": "DomainName","ParameterValue": domain},
        {"ParameterKey": "GroupName","ParameterValue": profile}
    ]
    account = boto3.client('sts').get_caller_identity()['Account']
    cf = boto3.client('cloudformation')
    cf_cert = boto3.client('cloudformation', region_name=region_cert)

    init(autoreset=True) # colorama: automatically reset style after each call

    # set which AWS credentials to use for this session
    # boto3.setup_default_session(profile_name=profile)

    print(Fore.GREEN + '\n'
        '###################################################\n'
        '######  Launching AWS CloudFormation Stacks  ######\n'
        '###################################################'
    )

    try:
        cf.describe_stacks(StackName=cf_stack)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stack(cf, cf_cert, cf_temp, cf_temp_cert, cf_stack,
                cf_stack_cert, params)
    else:
        print(Fore.RED + '\nStack already exists:', cf_stack)
        prompt = Fore.YELLOW + '\nUpdate|Delete|Cancel (U|D|C): ' + Fore.RESET
        while "input invalid":
            reply = str(input(prompt)).lower().strip()
            if reply[:1] == 'u':
                update_stack(cf, cf_stack, cf_temp, params)
                return True
            if reply[:1] == 'd':
                delete_stack(cf, cf_stack, domain)
                delete_stack_cert(cf_cert, cf_stack_cert)
                return False
            if reply[:1] == 'c':
                return False

def launch_stack(cf, cf_cert, cf_temp, cf_temp_cert, cf_stack, cf_stack_cert,
    params):
    print(Fore.CYAN + '\nAn ACM SSL/TSL certificate will be generated and '
        'validation email sent to:\n'
        '\n- WHOIS listed domain registrant & technical/admin contacts'
        '\n- Administrator, hostmaster, postmaster, webmaster and admin'
        '@your_domain_name\n'
        '\nYou will need to click the approval link on one of them for '
        'deployment to finish'
    )

    wait = input(Fore.YELLOW + '\nPress enter to continue...' + Fore.RESET)

    try:
        cf_cert.describe_stacks(StackName=cf_stack_cert)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            pass
    else:
        print(Fore.RED + '\nFound Existing Stack: ' + cf_stack_cert)
        delete_stack_cert(cf_cert, cf_stack_cert)

    print('')
    spin_start = '\nLaunching Stack: '+ cf_stack_cert
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    with open(cf_temp_cert, 'r') as f:
        cfn_temp_cert = f.read()

    cf_cert.create_stack(
        StackName=cf_stack_cert,
        TemplateBody=cfn_temp_cert,
        Parameters=params,
        TimeoutInMinutes=30,
        OnFailure='ROLLBACK'
    )

    waiter = cf_cert.get_waiter('stack_create_complete')
    waiter.wait(StackName=cf_stack_cert)

    spin_success = '\nStack Created: '+ cf_stack_cert
    spinner.succeed(text=spin_success)

    spin_start = '\n\nLaunching Stack: '+ cf_stack
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    with open(cf_temp, 'r') as f:
        cfn_temp = f.read()

    cf.create_stack(
        StackName=cf_stack,
        TemplateBody=cfn_temp,
        Parameters=params,
        TimeoutInMinutes=10,
        Capabilities=['CAPABILITY_NAMED_IAM'],
        OnFailure='ROLLBACK'
    )

    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Created: '+ cf_stack
    spinner.succeed(text=spin_success)

def update_stack(cf, cf_stack, cf_temp, params):
    try:
        print('')
        spin_start = '\nUpdating Stack: '+ cf_stack
        spinner = Halo(text=spin_start, spinner='circleHalves')
        spinner.start()

        with open(cf_temp, 'r') as f:
            template = f.read()

        cf.update_stack(
            StackName=cf_stack,
            TemplateBody=template,
            Parameters=params,
            Capabilities=['CAPABILITY_NAMED_IAM']
        )

        waiter = cf.get_waiter('stack_update_complete')
        waiter.wait(StackName=cf_stack)

        spin_success = '\nStack Updated: '+ cf_stack
        spinner.succeed(text=spin_success)
    except ClientError as e:
        error_string = 'No updates are to be performed.'
        if e.response['Error']['Message'].endswith(error_string):
            print(Fore.RED + ' ' + error_string)
            quit()

def delete_stack(cf, cf_stack, domain):
    print('')
    spin_start = '\nDeleting Stack: '+ cf_stack
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    # Bucket can't be deleted unless empty
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(domain)
    bucket_log = s3.Bucket(domain + '-log')
    bucket.objects.all().delete()
    bucket_log.objects.all().delete()

    cf.delete_stack(StackName=cf_stack)

    waiter = cf.get_waiter('stack_delete_complete')
    waiter.wait(StackName=cf_stack)

    spin_success = '\nStack Deleted: '+ cf_stack
    spinner.succeed(text=spin_success)

def delete_stack_cert(cf_cert, cf_stack_cert):
    print('')
    spin_start = '\nDeleting Stack: '+ cf_stack_cert
    spinner = Halo(text=spin_start, spinner='circleHalves')
    spinner.start()

    cf_cert.delete_stack(StackName=cf_stack_cert)

    waiter = cf_cert.get_waiter('stack_delete_complete')
    waiter.wait(StackName=cf_stack_cert)

    spin_success = '\nStack Deleted: '+ cf_stack_cert
    spinner.succeed(text=spin_success)

if __name__ == '__main__':
    main()
