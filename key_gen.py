#!/usr/bin/env python3

import boto3
from colorama import init, Fore
import os
import sys
import subprocess
import time

def main(site, home, repo_base):
    """Generates RSA public key to be used for git access to AWS CodeCommit
    repository. Generates locally, adds SSH alias to config, then uploads to
    AWS IAM user.
    """

    site_key = home + '.ssh/' + site + '-Key'
    iam = boto3.client('iam')

    response = iam.list_ssh_public_keys(UserName=site + '-Admin')
    # check if list inside dict has an element
    if len(response['SSHPublicKeys']) > 0:
        print(Fore.YELLOW + '\nExisting public key found for IAM user',
            Fore.YELLOW + site + '-Admin...')
        if input(Fore.GREEN + "\nRotate key (y/n)? "+ Fore.RESET) == "y":
            pub_key_id = response['SSHPublicKeys'][0]['SSHPublicKeyId']
            print('\nRemoving existing public key for IAM user',
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

            if repo_base in open(home + '.ssh/known_hosts').read():
                print('\nRemoving AWS CodeCommit host from ' + home +
                    '.ssh/known_hosts...\n')
                subprocess.run(
                    'ssh-keygen -R ' + repo_base,
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

        if sys.platform.startswith('darwin'):
            print('\nAdding new private key to ssh-agent & OSX keychain...')
            subprocess.run('/usr/bin/ssh-add -K ' + site_key, shell=True)
        elif sys.platform.startswith('linux'):
            print('\nAdding new private key to ssh-agent...')
            subprocess.run('ssh-add' + site_key, shell=True)

        print('\nSetting file mode on private key to 400...')
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
        os.chmod(site_key, 0o600)

        print(Fore.YELLOW + '\nWaiting 5 seconds for any AWS latency...')
        time.sleep( 5 )

        print('\nAdding AWS CodeCommit host to known_hosts and testing SSH '
            'config...\n')
        subprocess.run(
            'ssh -o StrictHostKeyChecking=no -tt ' + repo_base,
            shell=True
        )

if __name__ == '__main__':
    main()
