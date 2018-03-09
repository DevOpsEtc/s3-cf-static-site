#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
from colorama import init, Fore
from halo import Halo

def main():
    """Create/Update/Delete CloudFormation stack to deploy S3 static website.

    Launches a CloudFormation stack that creates:
        - One ACM SSL/TLS certificate
        - One IAM group
        - One IAM group policy
        - One IAM user
        - Two S3 buckets
        - Two CloudFront distributions
        - Two Route 53 DNS records
        - One CodeCommit repository

    Resources will be created in region us-east-1, for ACM
    certificate/CloudFront compatibility.

    Script checks for existing stack and if found, prompts to
    push CloudFormation template changes via an update or rollback deployment
    via a delete.
    """

    region_nm = 'us-east-1' # overide any local AWS config; needed for ACM cert
    profile_nm = 'Static-Site'
    sec_stk = profile_nm + '-Access'
    dep_stk = profile_nm + '-Deploy'
    pip_stk = profile_nm + '-Pipeline'
    stacks = [sec_stk, dep_stk, pip_stk]
    sec_tpl = 'cfn/security.cfn.yaml'
    dep_tpl = 'cfn/deploy.cfn.yaml'
    pip_tpl = 'cfn/pipeline.cfn.yaml'
    domain_nm = 'devopsetc.com'
    params =  [
        {"ParameterKey": "DomainName","ParameterValue": domain_nm},
        {"ParameterKey": "GroupName","ParameterValue": profile_nm},
        {"ParameterKey": "Region","ParameterValue": region_nm},
    ]
    account = boto3.client('sts').get_caller_identity()['Account']
    cf = boto3.client('cloudformation', region_name=region_nm)

    init(autoreset=True) # colorama: automatically reset style after each call

    # set which AWS credentials to use for this session
    # boto3.setup_default_session(profile_name=profile_nm)

    print(Fore.GREEN + '\n'
        '###################################################\n'
        '######  Launching AWS CloudFormation Stacks  ######\n'
        '###################################################'
    )

    try:
        cf.describe_stacks(StackName=dep_stk)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stacks(cf, sec_stk, dep_stk, pip_stk, dep_tpl, sec_tpl,
                pip_tpl, params, stacks)
    else:
        print(Fore.RED + '\nStack already exists:', dep_stk)
        prompt = Fore.YELLOW + '\nUpdate|Delete|Exit (U|D|X): ' + Fore.RESET
        while "input invalid":
            reply = str(input(prompt)).lower().strip()
            if reply[:1] == 'u':
                update_stacks(cf, sec_stk, dep_stk, pip_stk, dep_tpl, sec_tpl,
                    pip_tpl, params, stacks)
                return True
            if reply[:1] == 'd':
                delete_stacks(cf, sec_stk, dep_stk, pip_stk, domain_nm, stacks)
                return False
            if reply[:1] == 'x':
                return False

def launch_stacks(cf, sec_stk, dep_stk, pip_stk, dep_tpl, sec_tpl, pip_tpl,
    params, stacks):
    for stack in stacks:
        if stack == dep_stk:
            print('\nAn ACM SSL/TSL certificate will be generated and '
                'validation email sent to:\n'
                '\n- WHOIS listed domain registrant & technical/admin contacts'
                '\n- Administrator, hostmaster, postmaster, webmaster & admin'
                '@your_domain_name\n'
                '\nYou need to click the approval link in ONE of them for '
                'deployment to finish.'
            )
            wait = input(Fore.YELLOW + '\nPress enter to continue...')

        print('')
        spin_start = '\n\nLaunching Stack: '+ stack
        spinner = Halo(text=spin_start, spinner='circleHalves')
        spinner.start()

        if stack == sec_stk:
            src_tpl = sec_tpl

        if stack == dep_stk:
            src_tpl = dep_tpl

        if stack == pip_stk:
            src_tpl = pip_tpl

        with open(src_tpl, 'r') as f:
            tmp_tpl = f.read()

        cf.create_stack(
            StackName=stack,
            TemplateBody=tmp_tpl,
            Parameters=params,
            TimeoutInMinutes=15,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            OnFailure='ROLLBACK'
        )

        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack)

        spin_success = '\nStack Created: '+ stack
        spinner.succeed(text=spin_success)

def update_stacks(cf, dep_stk, sec_stk, pip_stk, sec_tpl, dep_tpl, pip_tpl,
    params, stacks):
    for stack in stacks:
        try:
            print('')
            spin_start = '\nUpdating Stack: '+ stack
            spinner = Halo(text=spin_start, spinner='circleHalves')
            spinner.start()

            if stack == sec_stk:
                src_tpl = sec_tpl

            if stack == dep_stk:
                src_tpl = dep_tpl

            if stack == pip_stk:
                src_tpl = pip_tpl

            with open(src_tpl, 'r') as f:
                tmp_tpl = f.read()

            cf.update_stack(
                StackName=stack,
                TemplateBody=tmp_tpl,
                Parameters=params,
                Capabilities=['CAPABILITY_NAMED_IAM']
            )

            waiter = cf.get_waiter('stack_update_complete')
            waiter.wait(StackName=stack)

            spin_success = '\nStack Updated: '+ stack
            spinner.succeed(text=spin_success)
        except ClientError as e:
            error_string = 'No updates are to be performed.'
            if e.response['Error']['Message'].endswith(error_string):
                print(Fore.RED + ' ' + error_string)
                quit()

def delete_stacks(cf, dep_stk, sec_stk, pip_stk, domain_nm, stacks):
    for stack in stacks:
        print('')
        spin_start = '\nDeleting Stack: '+ stack
        spinner = Halo(text=spin_start, spinner='circleHalves')
        spinner.start()

        if stack == dep_stk:
            # Bucket can't be deleted unless empty
            s3 = boto3.resource('s3', region_name=region_nm)

            try:
                s3.meta.client.head_bucket(Bucket=domain_nm)
            except ClientError as e:
                if e.response['Error']['Message'].endswith('does not exist'):
                    pass
            else:
                bucket = s3.Bucket(domain_nm)
                bucket.objects.all().delete()

            try:
                s3.meta.client.head_bucket(Bucket=domain_nm + '-log')
            except ClientError as e:
                if e.response['Error']['Message'].endswith('does not exist'):
                    pass
            else:
                bucket_log = s3.Bucket(domain_nm + '-log')
                bucket_log.objects.all().delete()

        cf.delete_stack(StackName=stack)

        waiter = cf.get_waiter('stack_delete_complete')
        waiter.wait(StackName=stack)

        spin_success = '\nStack Deleted: '+ stack
        spinner.succeed(text=spin_success)

if __name__ == '__main__':
    main()
