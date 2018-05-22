#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
from colorama import init, Fore
from halo import Halo
import os
import subprocess
import key_gen
import dev_env

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

    if not 'domain_name' in os.environ:
        print(Fore.YELLOW + '\nYou forgot to enter your domain name first:')
        print(Fore.YELLOW + '$ export domain_name=domain.com')
        exit()
    domain = os.environ['domain_name']
    domain_root = domain.split('.')[0]
    home = os.path.expanduser('~/')
    site_path = home + domain
    deploy_tpl = './deploy/site.cfn.yaml'
    region = 'us-east-1' # overide any local AWS config; needed for ACM cert
    repo_base = 'git-codecommit.' + region + '.amazonaws.com'
    repo_https = 'https://' + repo_base + '/v1/repos/' + domain
    repo_ssh = 'ssh://' + repo_base + '/v1/repos/' + domain
    site = 'Static-Site'

    account = boto3.client('sts').get_caller_identity()['Account']
    s3 = boto3.resource('s3', region_name=region)
    cf = boto3.client('cloudformation', region_name=region)

    params = [
    {"ParameterKey": "DomainName","ParameterValue": domain},
    {"ParameterKey": "RepoURL","ParameterValue": repo_https},
    {"ParameterKey": "SiteName","ParameterValue": site}
    ]

    print(Fore.WHITE + '\nStatic Site Deploy (' + domain + '):\n' + Fore.RESET)

    try:
        cf.describe_stacks(StackName=site)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            launch_stack(cf, deploy_tpl, domain, params, s3, site)
    else:
        print(Fore.YELLOW + 'Existing CloudFormation stack found:',
            Fore.YELLOW + site + '\n')
        prompt = Fore.GREEN + 'Skip, Update or Delete (S,U,D)? ' + Fore.RESET
        while True:
            reply = str(input(prompt)).lower()
            if reply[:1] == 'u':
                update_stack(cf, deploy_tpl, params, site)
                return True
            elif reply[:1] == 'd':
                if input(Fore.RED + "\nConfirm stack deletion (y/n)? ") == "y":
                    delete_stack(cf, domain, region, s3, site)
                    return True
                return False
            elif reply[:1] == 's':
                break
            else:
                print(Fore.RED + '\nInvalid... only S, U or D!\n')

    print(Fore.WHITE + '\nRSA Key Generation:' + Fore.RESET)
    key_gen.main(site, home, repo_base)

    if not os.path.isdir(site_path + '/src/.git/'):
        print(Fore.WHITE + '\nDev Environment Prep:' + Fore.RESET)
        dev_env.main(home, repo_ssh, site_path, domain)

    print(Fore.YELLOW + '\nGoodbye!')

def launch_stack(cf, deploy_tpl, domain, params, s3, site):
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
    buckets = [domain, 'log.' + domain, 'www.' + domain]
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
