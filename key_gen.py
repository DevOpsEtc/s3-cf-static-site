#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
from colorama import init, Fore
from halo import Halo
import os
import subprocess
import time

def main(site, home, region):
    """Generates RSA public key to be used for git access to AWS CodeCommit
    repository. Generates locally, adds SSH alias to config, then uploads to
    AWS IAM user.
    """

    site_key = home + '.ssh/' + site + '-Key'
    aws_ssh_host = 'git-codecommit.' + region + '.amazonaws.com'
    iam = boto3.client('iam')

    response = iam.list_ssh_public_keys(UserName=site + '-Admin')
    # check if list inside dict has an element
    if len(response['SSHPublicKeys']) > 0:
        print(Fore.YELLOW + '\nExisting public key found for IAM user',
            Fore.YELLOW + site + '-Admin...')
        if input(Fore.GREEN + "\nRotate key (y/n)? ") == "y":
            pub_key_id = response['SSHPublicKeys'][0]['SSHPublicKeyId']
            print(Fore.RESET + '\nRemoving existing public key for IAM user',
                site + '-Admin...')
            iam.delete_ssh_public_key(
                UserName=site + '-Admin',
                SSHPublicKeyId=pub_key_id
            )

            if os.path.isfile(site_key):
                print('\nRemoving existing private key:', site_key + '...')
                os.remove(site_key)

            if os.path.isfile(home + '.ssh/config.d/' + site):
                print('\nRemoving existing SSH config for AWS CodeCommit '
                    'host...')
                os.remove(home + '.ssh/config.d/' + site)

            if aws_ssh_host in open(home + '.ssh/known_hosts').read():
                print('\nRemoving AWS CodeCommit host from ' + home +
                    '.ssh/known_hosts...\n')
                subprocess.run(
                    'ssh-keygen -R ' + aws_ssh_host,
                    shell=True
                )

    response = iam.list_ssh_public_keys(UserName=site + '-Admin')
    if len(response['SSHPublicKeys']) == 0:
        key_pass = input('\nEnter passphrase for new private key: ')
        print('\nGenerating new private key:', site_key + '...\n')
        subprocess.run(
            'ssh-keygen -t rsa -b 2048 -f ' +site_key+ ' -P ' +key_pass,
            shell=True
        )

        print('Setting file mode on private key to 400...')
        os.chmod(site_key, 0o400)

        print('\nUploading new public key for IAM user', site + '-Admin...')
        with open(site_key + '.pub') as config:
            key = (config.read()
        )
        response = iam.upload_ssh_public_key(
            UserName=site + '-Admin',
            SSHPublicKeyBody=key
        )

        # Traverse dict inside dict to extract public key id
        pub_key_id = response['SSHPublicKey']['SSHPublicKeyId']

        print('\nRemoving local public key...')
        os.remove(site_key + '.pub')

        # Check for/make extra SSH config directory; octal mode permission syntax
        if not os.path.isdir(home + '.ssh/config.d/'):
            os.mkdir(home + '.ssh/config.d/', 0o700)

            # Prepend an include directive to default SSH config
            with open(home + '.ssh/config', 'r+') as config:
                first_line = config.readline()
                if first_line != 'Include config.d/*\n':
                    lines = config.readlines()
                    config.seek(0)
                    config.write('Include config.d/*\n')
                    config.write(first_line)
                    config.writelines(lines)

        print('\nAdding AWS public key ID to SSH config for git access to AWS '
            'CodeCommit repo...')

        with open(home + '.ssh/config.d/' + site, "w") as config:
            txt_lines = [
            'Host git-codecommit.*.amazonaws.com',
            '\n   User ' + pub_key_id,
            '\n   IdentityFile ' + site_key
            ]
            config.writelines(txt_lines)

        print('\nSetting file permissions on new SSH config to 600...')
        os.chmod(ssh_cfg, 0o600)

        print('\nAdding AWS CodeCommit host to ' + home +
            '.ssh/known_hosts...\n')
        subprocess.run(
            'ssh-keyscan -t rsa -H ' + aws_ssh_host + ' >> ~/.ssh/known_hosts',
            shell=True
        )

        print(Fore.YELLOW + '\nWaiting 5 seconds for AWS latency...')
        time.sleep( 5 )

        print('\nTesting new AWS CodeCommit SSH config...')
        subprocess.run('ssh ' + aws_ssh_host, shell=True)
        # subprocess.run(
        #     'ssh -o StrictHostKeyChecking=no -tt ' + aws_ssh_host,
        #     shell=True
        # )

if __name__ == '__main__':
    main()
