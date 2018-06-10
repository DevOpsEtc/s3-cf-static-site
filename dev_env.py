#!/usr/bin/env python3

from botocore.exceptions import ClientError
from colorama import init, Fore
import os
import subprocess
import sys

def main(cf, domain, home, repo_ssh, site_path, stack_cicd):

    """Bootstraps a development environment with package installation, sample
    static website, repo cloning and ad-hoc management commands.
    """

    logs = site_path + '/logs'  # raw log path
    report = '_report.html'     # log report name
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
        'hugo': 'https://gohugo.io/getting-started/installing',
        'yarn': 'https://yarnpkg.com/lang/en/docs/install'
    }

    for prereq, url in prereqs.items():
        try:
            subprocess.check_output(['type', '-p', prereq])
        except subprocess.CalledProcessError:
            print(Fore.RED + '\n' + prereq + ' is missing— install then '
                'rerun:')
            print(Fore.YELLOW + '\n' + url + Fore.RESET)
            exit()

    try:
        cf.describe_stacks(StackName=stack_cicd)
    except ClientError as e:
        if e.response['Error']['Message'].endswith('does not exist'):
            print(Fore.YELLOW + '\nMissing Stack: ' + stack_cicd)
            print(Fore.YELLOW + '\nRerun deploy script!')
            exit()

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
                    exit()
                else:
                    print(Fore.YELLOW + '\nKeeping your existing dev env!')
                    print(Fore.YELLOW + '\nGoodbye!')
                    exit()
                break
            elif reply[:1] == 's':
                print(Fore.YELLOW + '\nGoodbye!')
                exit()
            else:
                print(Fore.RED + '\nInvalid... only S or R!\n')

    print('\nCloning the new, empty AWS CodeCommit repo...\n')
    subprocess.run(
        'git clone ' + repo_ssh + ' ' + site_path + '/src',
        shell=True
    )

    print('\nVerifying local repo\'s new remote...\n')
    subprocess.run('git -C ' + site_path + '/src remote -v', shell=True)

    print('\nGenerating AWS CodeBuild buildspec for CI/CD workflow...')
    with open(site_path + '/deploy/build/buildspec_prod.yaml') as file:
        sub = (file.read()
            .replace('$hugo_ver', hugo_ver)
            .replace('$s3_bucket', domain)
            .replace('$cf_distro', cf_distro)
        )
    os.makedirs(site_path + '/src/config', exist_ok=True)
    with open(site_path + '/src/config/buildspec_prod.yaml', "w") as file:
        file.write(sub)

    print('\nGenerating new Hugo static site...')
    # force lets us install in non-empty directory, e.g. .git
    subprocess.run('hugo new site ' + site_path + '/src --force', shell=True)

    print('\nAdding a sample Hugo theme as a git submodule...')
    subprocess.run('git -C ' + site_path + '/src submodule add '
        + hugo_theme_url + ' themes/' + hugo_theme_name,
        shell=True
    )

    print("\nAdding a Hugo theme to your new Hugo site's config...")
    subprocess.run(
        'echo \'theme = "' + hugo_theme_name + '"\' >> ' + site_path + \
            '/src/config.toml',
        shell=True
    )

    print('\nCopying the example site from the Hugo theme...')
    subprocess.run('yes | cp -rf ' + site_path + '/src/themes/' + \
        hugo_theme_name + '/exampleSite/* ' + site_path + '/src',
        shell=True
    )

    print('\nInstalling dependences for yarn build...')
    subprocess.run(
        'cd ' + site_path + '/src/themes/' + hugo_theme_name + ' && yarn',
        shell=True
    )

    print('\nGenerating a gitignore for submodule, select theme files and '
        'yarn dependences...')
    with open(site_path + '/deploy/build/.gitignore') as file:
        sub = (file.read()
            .replace('$theme_name', hugo_theme_name)
        )
    with open(site_path + '/src/.gitignore', "w") as file:
        file.write(sub)

    print('\nStaging new files to local repo...')
    subprocess.run('git -C ' + site_path + '/src add -A', shell=True)

    print('\nCommitting staged files to local repo...\n')
    subprocess.run('git -C ' + site_path + '/src commit -m "test"', shell=True)

    print('\nPushing commit to remote AWS CodeCommit repo...\n')
    subprocess.run(
        'git -C ' + site_path + '/src push -f -u origin master',
        shell=True
    )

    print('\nGenerating site log analyzer script...')
    with open(site_path + '/deploy/build/log_analyzer.sh') as file:
        sub = (file.read()
            .replace('$domain', domain)
            .replace('$site_path', site_path)
            .replace('$logs', logs)
            .replace('$report', report)
        )
    os.makedirs(site_path + '/bin', exist_ok=True)
    with open(site_path + '/bin/log_analyzer.sh', "w") as file:
        file.write(sub)

    print('\nSetting file mode on site log analyzer script to 755...\n')
    os.chmod(site_path + '/bin/log_analyzer.sh', 0o755)

    if sys.platform.startswith('darwin'):
        dotfile = home + '.bash_profile'
    elif sys.platform.startswith('linux'):
        dotfile = home + '.bashrc'

    if not 'alias devkill' in open(dotfile).read():
        aliases = {
            'generate log analyzer locally: $ slr':
                'alias slr=\'' + site_path + '/bin/log_analyzer.sh\'\n',
            'delete log analyzer from S3 bucket: $ slrd':
                'alias slrd=\'aws s3 rm s3://' + domain + '/' + report +
                '\'\n',
            'start yarn/webpack/hugo dev watch: $ dev':
                'alias dev=\'cd ' + site_path + '/src; (hugo server &); \
                cd themes/' + hugo_theme_name + '; (yarn dev &); cd -; open \
                http://localhost:1313\'\n',
            'stop yarn/webpack/hugo dev watch: $ devkill':
                'alias devkill=\'(killall hugo node)\''
        }

        for k, v in aliases.items():
            print(Fore.YELLOW + 'Creating bash alias to ' + k + '...')
            with open(dotfile, "a") as file:
                file.write(v)

        print(Fore.YELLOW + '\nWorkflow: '
            '\n1. $ dev # start dev build system; enter to get prompt back'
            '\n2. Alter theme and/or create/update content'
            '\n3. Browser will automatically refresh with updates'
            '\n4. $ git add -A # stage changes'
            '\n5. $ git commit -m \'your commit message\' # commit changes'
            '\n6. $ git push origin master # or other branch\n'
        )

        print(Fore.YELLOW + '\nSource dotfile to load new aliases: '
            '$ source ' + dotfile
        )

if __name__ == '__main__':
    main()
