#!/usr/bin/env python3

import subprocess
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

    region = 'us-east-1' # overide any local AWS config; needed for ACM cert
    site = 'Static-Site'
    deploy_tpl = 'deploy.cfn.yaml'
    domain = 'devopsetc.com'
    params =  [
        {"ParameterKey": "DomainName","ParameterValue": domain},
        {"ParameterKey": "SiteName","ParameterValue": site},
    ]
    buckets = [domain, 'log.' + domain, 'www.' + domain]
    s3 = boto3.resource('s3', region_name=region)
    cf = boto3.client('cloudformation', region_name=region)

    # AWS_account = boto3.client('sts').get_caller_identity()['Account']

    # set which AWS credentials to use for this session
    # boto3.setup_default_session(profile_name=site)

    print(Fore.WHITE + '\n'
        '#############################################\n'
        '######     DevOps /etc Static Site     ######\n'
        '#############################################'
    )

    try:
        cf.describe_stacks(StackName=site)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stack(cf, deploy_tpl, params, s3, site)
    else:
        print (Fore.YELLOW + '\nStack Exists:' + site + '\n')
        prompt = Fore.GREEN + '[U]pdate, [D]elete or [C]ancel (U,D,C): '
        while True:
            reply = str(input(prompt)).lower().strip()
            if reply[:1] == 'u':
                update_stack(cf, deploy_tpl, params, site)
                return True
            elif reply[:1] == 'd':
                delete_stack(cf, domain, region, s3, site)
                return True
            elif reply[:1] == 'c':
                return False
            else:
                print('\nInvalid, Try again\n')

def launch_stack(cf, deploy_tpl, params, s3, site):
    print(Fore.GREEN + '\n'
        'Multiple certificate validation emails will be sent to:\n\n'
        '  - WHOIS listed domain contacts\n'
        '  - Administrator|hostmaster|postmaster|webmaster|admin'
        '@your_domain_name\n\n'
        'Click the approval link in ONE in order to finish deployment.'
    )
    wait = input(Fore.YELLOW + '\nPress enter to continue...\n')

    with open(deploy_tpl, 'r') as f:
        tmp_tpl = f.read()

    try:
        cf.create_stack(
            StackName=site,
            TemplateBody=tmp_tpl,
            Parameters=params,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            OnFailure='ROLLBACK'
        )

        spinner = Halo(text='Launching: '+ site, color='green').start()
        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(StackName=site)
        spinner.succeed(text='Deployed: '+ site)
    except ClientError as e:
        error_string = 'Waiter encountered a terminal failure state'
        if e.response['Error']['Message'].endswith(error_string):
            print(Fore.RED + error_string + '\nSee AWS web console')
        else:
            print(Fore.RED + e.response['Error']['Message'])

    files = {
        'index.html': 'index.html',
        'image/gear_logo.png': 'image/gear_logo.png'
    }
    for k, v in files.items():
        print('\nCopying file: ' + k + ' => ' + domain + '/' + k)
        s3.meta.client.upload_file('build/'+k, domain, v)

def update_stack(cf, deploy_tpl, params, site):
    with open(deploy_tpl, 'r') as f:
        tmp_tpl = f.read()

    try:
        cf.update_stack(
            StackName=site,
            TemplateBody=tmp_tpl,
            Parameters=params,
            Capabilities=['CAPABILITY_NAMED_IAM']
        )

        spinner = Halo(text='Updating: '+ site, color='green').start()
        waiter = cf.get_waiter('stack_update_complete')
        waiter.wait(StackName=site)
        spinner.succeed(text='Updated: '+ site)
    except ClientError as e:
        error_string = 'No updates are to be performed.'
        if e.response['Error']['Message'].endswith(error_string):
            print(Fore.WHITE + '\n' + site + ' => ' + error_string + '\n')
        else:
            print(Fore.RED + e.response['Error']['Message'])

def delete_stack(cf, domain, region, s3, site):
    for b in buckets:
        try:
            s3.meta.client.head_bucket(Bucket=b)
        except ClientError as e:
            if e.response['Error']['Message'].endswith('does not exist'):
                pass
        else:
            # Bucket can't be deleted unless empty
            bucket = s3.Bucket(b)
            bucket.objects.all().delete()

    cf.delete_stack(StackName=site)

    spinner = Halo(text='Deleting: '+ site, color='green').start()
    waiter = cf.get_waiter('stack_delete_complete')
    waiter.wait(StackName=site)
    spinner.succeed(text='Deleted: '+ site)

if __name__ == '__main__':
    main()
