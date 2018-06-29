#!/usr/bin/env python3

# include standard modules
import getpass
import os
import subprocess
import sys
import time

# include 3rd party modules
import boto3
from colorama import init, Fore

def main():
    """Generates RSA public key to be used for git access to AWS CodeCommit
    repository. Generates locally, adds SSH alias to config, then uploads to
    AWS IAM user.
    """
    home = os.path.expanduser('~/')
    site = 'Static-Site'
    site_key = home + '.ssh/' + site + '-Key'
    repo_base = 'git-codecommit.us-east-1.amazonaws.com'
    iam = boto3.client('iam')
    response = iam.list_ssh_public_keys(UserName=site + '-Admin')

    print(Fore.WHITE + '\nRSA Key Generation:' + Fore.RESET)

    # check if list inside dict has an element
    if len(response['SSHPublicKeys']) > 0:
        print(Fore.YELLOW + '\nExisting key found for AWS IAM user: ' + site +
            '-Admin' + '\n')
        prompt = Fore.GREEN + 'Skip or Rotate (S/R)? ' + Fore.RESET
        while True:
            reply = str(input(prompt)).lower()
            if reply[:1] == 'r':
                pub_key_id = response['SSHPublicKeys'][0]['SSHPublicKeyId']
                print('\nRemoving existing public key for IAM user',
                    site + '-Admin...')
                iam.delete_ssh_public_key(
                    UserName=site + '-Admin',
                    SSHPublicKeyId=pub_key_id
                )

                print('\nRemoving existing private key from ssh-agent...')
                subprocess.run(
                    '[[ $(ssh-add -l | grep \' '+ site_key + ' \') ]] \
                        && ssh-add -d ' + site_key,
                    shell=True
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
                    subprocess.run('ssh-keygen -R ' + repo_base, shell=True)
                break
            elif reply[:1] == 's':
                break
            else:
                print(Fore.RED + '\nInvalid... only S or R!\n')

    response = iam.list_ssh_public_keys(UserName=site + '-Admin')
    if len(response['SSHPublicKeys']) == 0:
        key_pass = getpass.getpass('\nEnter passphrase for new private key: ')
        print('\nGenerating new private key:', site_key + '...\n')
        subprocess.run(
            'ssh-keygen -t rsa -b 2048 -f ' + site_key + ' -C ' + site_key + \
                ' -P ' + key_pass,
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

        print('\nSetting file mode on new SSH config to 600...')
        os.chmod(site_key, 0o600)

        print(Fore.YELLOW + '\nPadding 10 seconds for any '
            'AWS latency...' + Fore.RESET)
        time.sleep( 10 )

        print('\nAdding AWS CodeCommit host to known_hosts and testing SSH '
            'config...\n')
        subprocess.run(
            'ssh -o StrictHostKeyChecking=no -tt ' + repo_base,
            shell=True
        )

if __name__ == '__main__':
    main()
