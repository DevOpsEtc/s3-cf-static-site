#!/usr/bin/env python3

# include standard modules
import os
import shutil
import subprocess
import sys

# include 3rd party modules
from botocore.exceptions import ClientError
from colorama import init, Fore

def main(cf, domain, email, home, repo_ssh, site_path, stack_cicd):

    """Bootstraps a development environment with package installation, sample
    static website, revision control and source code build system.
    """

    hugo_theme_name = 'hugo-nuo'
    hugo_theme_repo = 'laozhu/hugo-nuo' # https://themes.gohugo.io
    hugo_theme_url = 'https://github.com/' + hugo_theme_repo
    hugo_ver = subprocess.check_output(
        'curl --silent \
            "https://api.github.com/repos/gohugoio/hugo/releases/latest" | \
            grep "tag_name" | awk -Fv \'{gsub("\\"\,", ""); print $2}\'',
          shell=True,
          universal_newlines=True
    ).strip()
    cf_distro = subprocess.check_output(
        'aws cloudfront list-distributions --query "DistributionList.Items[? \
            contains(Aliases.Items, \'' + domain + '\')].Id" --output text',
          shell=True,
          universal_newlines=True
    ).strip()
    prereqs = {
        'aws': 'https://docs.aws.amazon.com/cli/latest/userguide/installing.html',
        'goaccess': 'https://goaccess.io/get-started',
        'hugo': 'https://gohugo.io/getting-started/installing',
        'yarn': 'https://yarnpkg.com/lang/en/docs/install'
    }

    print(Fore.WHITE + '\nDev Environment Prep:' + Fore.RESET)

    try:
        cf.describe_stacks(StackName=stack_cicd)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            print(Fore.YELLOW + '\nMissing Stack: ' + stack_cicd)
            print(Fore.YELLOW + '\nRerun install!')
            sys.exit(0)

    if os.path.isdir(site_path + '/bin'):
        print(Fore.YELLOW + '\nExisting dev env found!\n')
        prompt = Fore.GREEN + 'Skip or Remove/Rebuild (S/R)? ' + Fore.RESET
        while True:
            reply = str(input(prompt)).lower()
            if reply[:1] == 'r':
                if input(Fore.RED + "\nAfter removing you'll need to delete "
                    "the Static-Site-CICD stack BEFORE you can rebuild the "
                    "dev env!\n"
                    '\nStill want to remove (y/n)? ' + Fore.RESET) == "y":
                    subprocess.run(
                        'rm -rf ' + site_path + '/{bin,src}',
                        shell=True
                    )
                    print(Fore.YELLOW + '\nYour dev env was removed! Goodbye.')
                    sys.exit(0)
                else:
                    print(Fore.YELLOW + '\nKeeping your existing dev env!')
                    print(Fore.YELLOW + '\nGoodbye!')
                    sys.exit(0)
                break
            elif reply[:1] == 's':
                print(Fore.YELLOW + '\nGoodbye!')
                sys.exit(0)
            else:
                print(Fore.RED + '\nInvalid... only S or R!\n')

    print('\nChecking prereqs...\n')
    for k, v in prereqs.items():
        try:
            subprocess.check_output(['type', '-p', k])
            print(k + Fore.GREEN + ' \u2714' + Fore.RESET)
        except subprocess.CalledProcessError:
            print(Fore.RED + '\n' + k + ' is missing— install then '
                'rerun:')
            print(Fore.YELLOW + '\n' + v + Fore.RESET)
            sys.exit(1)

    print('\nCopying build files to ' + site_path + '...\n')

    build_content = {
    'bin': '/bin',
    'src': '/src',
    'build': '/src/build'
    }

    for k, v in build_content.items():
        shutil.copytree(site_path + '/deploy/build/' + k, site_path + v)
        print(k + ' => ' + site_path + v + Fore.GREEN + ' \u2714' + Fore.RESET)

    print('\nCustomizing AWS CodeBuild buildspec for CI/CD workflow...')
    with open(site_path + '/src/build/buildspec_prod.yaml') as file:
        sub = (file.read()
        .replace('$hugo_ver', hugo_ver)
        .replace('$s3_bucket', domain)
        .replace('$cf_distro', cf_distro)
        )
        with open(site_path + '/src/build/buildspec_prod.yaml', "w") as file:
            file.write(sub)

    print('\nCustomizing site development tools script...')
    with open(site_path + '/bin/dev_tools.py') as file:
        sub = (file.read()
            .replace('$site_deploy', site_path + '/deploy')
            .replace('$domain', domain)
            .replace('$email', email)
        )
    with open(site_path + '/bin/dev_tools.py', "w") as file:
        file.write(sub)

    print('\nCustomizing Hugo site configuration...')
    with open(site_path + '/src/config.toml') as file:
        sub = (file.read()
            .replace('$domain', domain)
        )
    with open(site_path + '/src/config.toml', "w") as file:
        file.write(sub)

    print('\nInstalling dependences for build system...\n')
    os.chdir(site_path + '/src/build')
    subprocess.run('yarn', shell=True)

    print('\nCreating local Git code repository...\n')
    subprocess.run('git -C ' + site_path + '/src init', shell=True)

    print('\nAdding sample Hugo theme as git submodule...\n')
    subprocess.run(
        'git -C ' + site_path + '/src submodule add -f ' + hugo_theme_url +
        ' themes/' + hugo_theme_name,
        shell=True
    )

    print('\nAdding ' + site_path + '/src files to local repo staging...')
    subprocess.run('git -C ' + site_path + '/src add .', shell=True)

    print('\nCommiting staged files to local repo...\n')
    subprocess.run('git -C ' + site_path + '/src commit -m "Initial commit"',
        shell=True
    )

    print('\nAdding remote AWS CodeCommit repo to local git repo...')
    subprocess.run('git -C ' + site_path + '/src remote add origin ' + repo_ssh,
        shell=True
    )

    print('\nVerifying local repo\'s new remote...\n')
    subprocess.run('git -C ' + site_path + '/src remote -v', shell=True)

    if sys.platform.startswith('darwin'):
        dotfile = home + '.bash_profile'
    elif sys.platform.startswith('linux'):
        dotfile = home + '.bashrc'

    if not 'alias site' in open(dotfile).read():
        print('\nAdding bash aliases for site development...\n')

        aliases = {
            '$ site # run development tool script':
                'alias site=\'' + site_path + '/bin/dev_tools.py\'\n',
            '$ sitego # change directory to site source':
                'alias sitego=\'cd ' + site_path + '/src && ls -l\''
        }

        for k, v in aliases.items():
            with open(dotfile, "a") as file:
                file.write(v)
            print(Fore.GREEN + k + Fore.GREEN + ' \u2714' + Fore.RESET)

        print(Fore.YELLOW + '\nPlease source your dotfile to load aliases...\n'
            '$ source ' + dotfile + Fore.RESET
        )

    print(Fore.GREEN + '\n$ site -h # display site cli help ' +
        Fore.RESET + '\n\nEnjoy!'
    )

    print('\nPushing commit to remote AWS CodeCommit repo...\n')
    subprocess.run(
        'git -C ' + site_path + '/src push -u origin master',
        shell=True
    )

if __name__ == '__main__':
    main()
